from minio import Minio
from pinecone import Pinecone, ServerlessSpec, Index
import os
from functools import lru_cache
import logging


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


@lru_cache(maxsize=4)
def get_pinecone_client() -> Pinecone:
    """
    Dependency function to configure and serve Pinecone client. Client is cached for reuse.
    """
    return Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


@lru_cache(maxsize=8)  # Can increase cache size if we have more indexes
def get_pinecone_index(
    client: str,
    pinecone_client: Pinecone,
    logger: logging.Logger,
    dimension: int | None = None,
    metric: str = "cosine",
    cloud: str = "aws",
    region: str = "us-east-1",
) -> Index:
    """
    Creates a Pinecone index if it doesn't already exist.

    Args:
        client (str): Name of the index.
        pinecone_client (Pinecone): Pinecone client used to connect to index.
        logger (Logger): For logging.
        dimension (int | None): Dimensionality of the vectors to be indexed. Defaults to None.
        metric (str): Distance metric to use. Defaults to "cosine".
        cloud (str): Cloud provider for infra. Defaults to "aws".
        region (str): Region where pod will be located. Defaults to "us-east-1".
    """
    existing_index_names = [idx.name for idx in pinecone_client.list_indexes()]
    logger.debug(f"Index list {existing_index_names}")
    if client not in existing_index_names:
        pinecone_client.create_index(
            name=client,
            dimension=DIMENSIONS[EMBEDDING_MODEL] if dimension is None else dimension,
            metric=metric,
            spec=ServerlessSpec(cloud=cloud, region=region),
        )
        logger.info(f"Created index for client {client}.")
    logger.debug(f"Index exists for client {client}.")

    return Index(client)
