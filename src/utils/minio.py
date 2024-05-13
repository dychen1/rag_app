from minio import Minio
import os
from functools import lru_cache


@lru_cache(maxsize=4)
def get_minio_client() -> Minio:
    """
    Dependency function to configure and serve Minio client. Client is cached for resuse.

    Can cache multiple Minio clients in case different customers/projects have different buckets.
    """
    return Minio(
        endpoint=f"{os.getenv('MINIO_HOSTNAME')}:{os.getenv('MINIO_API_PORT')}",
        access_key=os.getenv("MINIO_ROOT_USER"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
        secure=False,  # since its localhost, no https
    )
