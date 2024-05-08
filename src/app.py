import os
from pathlib import Path

from fastapi import FastAPI
from minio import Minio
from minio.error import S3Error

from src.utils.env import load_env_vars

# Configure your MinIO client
minio_env = Path(__file__).parent.parent / "etc" / "minio.env"
load_env_vars(str(minio_env))
minio_client = Minio(
    endpoint=f"{os.getenv('MINIO_HOSTNAME')}:{os.getenv('MINIO_PORT')}",
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    secure=False,  # since its localhost, no https
)


app = FastAPI()
