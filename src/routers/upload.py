from fastapi import HTTPException, Depends, UploadFile, APIRouter, Form
from minio.error import S3Error
from minio import Minio
from minio.versioningconfig import VersioningConfig
from minio.commonconfig import ENABLED
from src.utils.minio import get_minio_client
from src.models.response import UploadResponse


SUPPORT_FILE_TYPES: list[str] = ["pdf", "tiff", "png", "jpeg"]
router = APIRouter()


@router.post("/upload")
def upload_files(
    files: list[UploadFile],
    client: str = Form(...),
    project: str = Form(...),
    minio_client: Minio = Depends(get_minio_client),
) -> UploadResponse:
    signed_urls: list[str] = []
    empty_files: list[str] = []
    unsupported_files: list[str] = []
    files_too_large: list[str] = []
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

        if file.size > 1000 * 1024 * 1024:  # Set file size limit 1GB, needs a front end check if user facing
            files_too_large.append(file.filename)
            continue

        try:  # Upload file to minio
            bucket_name = f"{client}-{project}"
            ensure_bucket_exists(bucket_name, minio_client)

            # Create a new object and stream data to it
            minio_client.put_object(
                bucket_name=bucket_name,
                object_name=file.filename,
                data=file.file,
                length=-1,
                part_size=1024 * 1024 * 10,  # Stream 10MB chunks
            )

            # Generate a presigned URL for accessing the uploaded file
            file_url = minio_client.presigned_get_object(bucket_name, file.filename)
            signed_urls.append(file_url)
            successfully_uploaded_files.append(file.filename)
        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}")

    # Logging
    details: str = ""
    if empty_files:
        details += f"Empty file(s): {empty_files}. "
    if unsupported_files:
        details += f"File(s) with unsupported extension: {unsupported_files}. "
    if files_too_large:
        details += f"File(s) which were too large: {files_too_large}. "

    if details == "":
        details += "All files successfully uploaded."
    else:
        details += f"Successfully uploaded files: {successfully_uploaded_files}."

    return UploadResponse(signed_urls=signed_urls, details=details)


def ensure_bucket_exists(bucket_name: str, minio_client: Minio) -> None:
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            minio_client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Failed to check/create bucket: {e}")
