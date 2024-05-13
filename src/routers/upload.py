from fastapi import HTTPException, Depends, UploadFile, APIRouter, Form
from minio.error import S3Error
from minio import Minio
from minio.versioningconfig import VersioningConfig
from minio.commonconfig import ENABLED
from typing import BinaryIO

from src.models.response import UploadResponse
from src.utils.minio import get_minio_client
from src.utils.decorators import async_retry


SUPPORT_FILE_TYPES: list[str] = ["pdf", "tiff", "png", "jpeg", "json"]  # Added json to be able to upload samples
RETRY_ATTEMPTS: int = 3  # Try to upload file 3 times if upload to Minio fails
router = APIRouter()


@router.post("/upload")
async def upload_files(
    files: list[UploadFile],
    client: str = Form(...),
    project: str = Form(...),
    minio_client: Minio = Depends(get_minio_client),
) -> UploadResponse:
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
        await ensure_bucket_exists(minio_client, bucket_name)
        try:
            file_name: str = file.filename
            file_data: BinaryIO = file.file
            file_url: str = await upload_to_minio(minio_client, bucket_name, file_data, file_name)
            signed_urls.append(file_url)
            successfully_uploaded_files.append(file.filename)
        except HTTPException as e:
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

    return UploadResponse(signed_urls=signed_urls, details=details)


@async_retry(max_attempts=3, initial_delay=2, backoff_factor=2)
async def upload_to_minio(minio_client: Minio, bucket_name: str, file_data: BinaryIO, file_name: str) -> str:
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


async def ensure_bucket_exists(minio_client: Minio, bucket_name: str) -> None:
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            minio_client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Failed to check/create bucket: {e}")
