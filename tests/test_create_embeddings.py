import json
import pytest
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
