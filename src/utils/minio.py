from minio import Minio
from pathlib import Path
from src.utils.env import load_env_vars
import os
from functools import lru_cache


@lru_cache(maxsize=4)
def get_minio_client() -> Minio:
    """
    Dependency function to configure and serve Minio client. Client is cached for resuse.
    """
    minio_env = Path(__file__).parent.parent.parent / "etc" / "minio.env"
    load_env_vars(str(minio_env))
    return Minio(
        endpoint=f"{os.getenv('MINIO_HOSTNAME')}:{os.getenv('MINIO_API_PORT')}",
        access_key=os.getenv("MINIO_ROOT_USER"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
        secure=False,  # since its localhost, no https
    )
