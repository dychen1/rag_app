from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def test_upload_files_success(test_app: TestClient) -> None:
    """Test successful file upload."""
    files = [
        ("files", ("test.txt", b"Test file content", "text/plain")),
    ]
    response = test_app.post(
        "/upload",
        data={"client": "test_client", "project": "test_project"},
        files=files,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["signed_urls"] == ["http://test_minio.com/test_file_url"]
    assert data["details"] == "All files successfully uploaded."


def test_upload_files_unsupported_file_type(test_app: TestClient) -> None:
    """Test uploading an unsupported file type."""
    files = [
        ("files", ("test.exe", b"Unsupported file type", "application/octet-stream")),
        ("files", ("test.txt", b"Test file content", "text/plain")),
    ]
    response = test_app.post(
        "/upload",
        data={"client": "test_client", "project": "test_project"},
        files=files,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["signed_urls"] == ["http://test_minio.com/test_file_url"]
    assert (
        data["details"]
        == "1 file(s) with unsupported extension: ['test.exe']. 1 successfully uploaded files: ['test.txt']."
    )


def test_upload_empty_file(test_app: TestClient) -> None:
    """Test uploading an empty file."""
    files = [
        ("files", ("empty.txt", b"", "text/plain")),
    ]
    response = test_app.post(
        "/upload",
        data={"client": "test_client", "project": "test_project"},
        files=files,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["signed_urls"] == []
    assert data["details"] == "1 empty file(s): ['empty.txt']. 0 successfully uploaded files: []."


def test_upload_files_large_file(test_app: TestClient, monkeypatch) -> None:
    """Test uploading a file that is too large."""
    monkeypatch.setattr("src.routers.upload.FILE_SIZE_LIMIT", 1)  # 1 byte limit for testing

    files = [
        ("files", ("large.txt", b"A lot of text", "text/plain")),
    ]
    response = test_app.post(
        "/upload",
        data={"client": "test_client", "project": "test_project"},
        files=files,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["signed_urls"] == []
    assert data["details"] == "1 file(s) which were too large: ['large.txt']. 0 successfully uploaded files: []."
