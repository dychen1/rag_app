import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.routers import upload, create_embeddings
from src.utils.clients import get_minio_client


@pytest.fixture
def mock_minio_client():
    """Fixture to mock Minio client."""
    with patch("src.utils.clients.get_minio_client") as mock:
        yield mock


@pytest.fixture
def mock_minio_methods(mock_minio_client):
    """Fixture to mock Minio methods."""
    minio_client_instance = mock_minio_client.return_value
    minio_client_instance.bucket_exists.return_value = False
    minio_client_instance.make_bucket.return_value = None
    minio_client_instance.set_bucket_versioning.return_value = None
    minio_client_instance.put_object.return_value = None
    minio_client_instance.presigned_get_object.return_value = "http://test_minio.com/test_file_url"
    return minio_client_instance


@pytest.fixture
def mock_pinecone_index():
    """Fixture to mock Pinecone index."""
    with patch("src.utils.clients.get_pinecone_index") as mock:
        yield mock


@pytest.fixture
def mock_aiohttp_session():
    """Fixture to mock aiohttp ClientSession."""
    with patch("aiohttp.ClientSession.get") as mock:
        yield mock


@pytest.fixture
def test_app(mock_minio_methods, mock_pinecone_index, mock_aiohttp_session):
    app = FastAPI()
    app.include_router(upload.router, dependencies=[Depends(lambda: None)])  # Placeholder dependency
    app.dependency_overrides[get_minio_client] = lambda: mock_minio_methods
    app.include_router(create_embeddings.router)
    return TestClient(app)
