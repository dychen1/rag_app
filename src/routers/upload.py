from fastapi import HTTPException, Depends, UploadFile, APIRouter, Form
from minio import Minio
from minio.versioningconfig import VersioningConfig
from minio.commonconfig import ENABLED
from pathlib import Path
from typing import BinaryIO

from src.models.response import UploadResponse
from src.utils.decorators import async_retry
from src.utils.logger import init_logger
from src.utils.clients import get_minio_client


SUPPORT_FILE_TYPES: list[str] = ["pdf", "tiff", "png", "jpeg", "txt"]  # Added txt for testing
router = APIRouter()
logger = init_logger(file_path=Path(__file__).parent.parent.parent / "etc" / "logs")


@router.post("/upload")
async def upload_files(
    files: list[UploadFile],
    client: str = Form(...),
    project: str = Form(...),
    minio_client: Minio = Depends(get_minio_client),
) -> UploadResponse:
    """
    Upload files to a Minio bucket associated with a client and project and returns signed URLs.

    Args:
        files (list[UploadFile]): List of files to be uploaded.
        client (str): Client identifier for the bucket.
        project (str): Project identifier for the bucket.
        minio_client (Minio): Minio client instance, injected via dependency.

    Returns:
        UploadResponse: Response object containing signed URLs and details of the upload process.

    Workflow:
        - Iterate through list of files.
        - Perform checks on each file.
        - Make sure Minio bucket exists for the client+project, creates one if it doesnt.
        -
    """
    signed_urls: list[str] = []
    empty_files: list[str] = []
    unsupported_files: list[str] = []
    files_too_large: list[str] = []
    failed_upload_files: list[str] = []
    successfully_uploaded_files: list[str] = []

    for file in files:
        # File checks
        if file.filename is None or file.size is None:
            raise HTTPException(status_code=400, detail="No file provided or file has no name.")

        if file.filename == "" or file.size == 0:  # Empty file check
            empty_files.append(file.filename)
            continue

        file_extension: str = file.filename.split(".")[-1].lower()
        if file_extension not in SUPPORT_FILE_TYPES:
            unsupported_files.append(file.filename)
            continue

        if file.size > 1000 * 1024 * 1024:
            files_too_large.append(file.filename)
            continue

        bucket_name = f"{client}-{project}"
        try:
            await _ensure_bucket_exists(minio_client, bucket_name)
        except HTTPException as e:
            msg = f"Failed to check/create bucket:\n{e}"
            logger.error(msg)
            raise HTTPException(status_code=500, detail=msg)

        try:
            file_name: str = file.filename
            file_data: BinaryIO = file.file
            file_url: str = await _upload_to_minio(minio_client, bucket_name, file_data, file_name)
            signed_urls.append(file_url)
            successfully_uploaded_files.append(file.filename)
        except HTTPException as e:
            logger.error(f"Failed to upload {file.filename} to Minio bucket:\n{e}")
            failed_upload_files.append(file.filename)

    # Logging
    details: str = ""
    if empty_files:
        details += f"{len(empty_files)} empty file(s): {empty_files}. "
    if unsupported_files:
        details += f"{len(unsupported_files)} file(s) with unsupported extension: {unsupported_files}. "
    if files_too_large:
        details += f"{len(files_too_large)} file(s) which were too large: {files_too_large}. "
    if failed_upload_files:
        details += f"{len(failed_upload_files)} file(s) failed during upload: {failed_upload_files}. "

    if details == "":
        details += "All files successfully uploaded."
    else:
        details += f"{len(successfully_uploaded_files)} successfully uploaded files: {successfully_uploaded_files}."
    logger.info(details)

    return UploadResponse(signed_urls=signed_urls, details=details)


@async_retry(logger, max_attempts=3, initial_delay=1, backoff_factor=2)
async def _upload_to_minio(minio_client: Minio, bucket_name: str, file_data: BinaryIO, file_name: str) -> str:
    """
    Uploads a file to a Minio bucket and generates a presigned URL for accessing the uploaded file.

    Args:
        minio_client (Minio): Minio client instance.
        bucket_name (str): Name of the bucket to upload the file to.
        file_data (BinaryIO): File data to be uploaded in binary.
        file_name (str): Name of the file to be uploaded.

    Returns:
        str: Presigned URL for accessing the uploaded file.
    """
    # Create a new object and stream data to it
    minio_client.put_object(
        bucket_name=bucket_name,
        object_name=file_name,
        data=file_data,
        length=-1,  # -1 is used when the size of file uploads is unknown
        part_size=1024 * 1024 * 10,  # Upload file in 10MB chunks
    )
    # Generate a presigned URL for accessing the uploaded file, using default 7 day expiration
    return minio_client.presigned_get_object(bucket_name, file_name)


@async_retry(logger, max_attempts=2, initial_delay=1, backoff_factor=2)
async def _ensure_bucket_exists(minio_client: Minio, bucket_name: str) -> None:
    """
    Ensure that a specified Minio bucket exists and creates it if not with versioning enabled.

    Args:
        minio_client (Minio): Minio client instance.
        bucket_name (str): Name of the bucket to check/create.
    """
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
        minio_client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
