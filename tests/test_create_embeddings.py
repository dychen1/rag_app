import json
import pytest
import pytest_asyncio
from langchain_core.documents import Document
from pathlib import Path

from src.routers.create_embeddings import _add_metadata, _mock_ocr_extraction
from src.utils.hashers import hash_string


ETC_PATH = Path(__file__).parent.parent / "etc"


def test_add_metadata():
    documents = [Document(page_content="Content 1"), Document(page_content="Content 2")]
    file_name = "example.txt"
    timestamp = 1625097600

    ids, updated_documents = _add_metadata(documents, file_name, timestamp)

    expected_ids = [hash_string(f"{i}_{file_name}") for i in range(len(documents))]
    assert ids == expected_ids

    for idx, doc in enumerate(updated_documents):
        assert doc.metadata == {"name": file_name, "chunk_id": idx, "timestamp": timestamp}


@pytest.mark.asyncio
async def test_mock_ocr_extraction_建築基準法施行令():
    file_name = "建築基準法施行令.pdf"
    result = await _mock_ocr_extraction(file_name)

    with open(ETC_PATH / "ocr_samples" / "建築基準法施行令.json") as file:
        data = json.load(file)
        expected_content = data["analyzeResult"]["content"]
    assert result.page_content == expected_content


@pytest.mark.asyncio
async def test_mock_ocr_extraction_東京都建築安全条例():
    file_name = "東京都建築安全条例.pdf"
    result = await _mock_ocr_extraction(file_name)

    with open(ETC_PATH / "ocr_samples" / "東京都建築安全条例.json") as file:
        data = json.load(file)
        expected_content = data["analyzeResult"]["content"]
    assert result.page_content == expected_content


@pytest.mark.asyncio
async def test_mock_ocr_extraction_experiential_colearning():
    file_name = "experiential_colearning.txt"
    result = await _mock_ocr_extraction(file_name)
    with open(ETC_PATH / "sample_files" / file_name) as file:
        expected_content = file.read()
    assert result.page_content == expected_content


# from unittest.mock import patch, MagicMock, AsyncMock
# from fastapi import HTTPException
# from src.models.requests import CreateEmbeddingsRequest
# from src.utils.hashers import hash_string

# def _add_metadata(documents: list[Document], file_name: str, timestamp: int) -> tuple[list[str], list[Document]]:
#     """
#     Adds metadata to each document in the provided list and generates unique IDs for each document chunk.

#     This function updates the metadata of each document in the `documents` list with the provided `file_name`,
#     a unique chunk identifier, and a `timestamp`. Additionally, it generates a list of unique IDs for each
#     document chunk by hashing the chunk ID and file name.

#     Args:
#         documents (list[Document]): A list of Document objects to which metadata will be added.
#         file_name (str): The name of the file to be included in the metadata of each document.
#         timestamp (int): A timestamp to be included in the metadata of each document.

#     Returns:
#         tuple[list[str], list[Document]]: A tuple containing two elements:
#             - A list of unique string IDs generated for each document chunk.
#             - The list of Document objects with updated metadata.

#     Example:
#         documents = [Document(page_content="Content 1"), Document(page_content="Content 2")]
#         file_name = "example.txt"
#         timestamp = 1625097600
#         ids, updated_documents = _add_metadata(documents, file_name, timestamp)
#         print(ids)  # Output: [hashed_id_0, hashed_id_1]
#         print(updated_documents[0].metadata)  # Output: {"name": "example.txt", "chunk_id": 0, "timestamp": 1625097600}
#     """
#     ids: list[str] = []
#     for idx, doc in enumerate(documents):
#         doc.metadata = {"name": file_name, "chunk_id": idx, "timestamp": timestamp}
#         ids.append(hash_string(f"{idx}_{file_name}"))  # Hash ids so that we can represent doc name in ASCII
#     logger.debug(f"Generated {len(ids)} id's for documents chunks: {ids}.")
#     return (ids, documents)
