import pytest
from langchain_core.documents import Document
from dotenv import dotenv_values
from pathlib import Path

from src.utils.chain import chunk_content
from src.utils.hashers import hash_string
from src.utils.load_env import load_env_vars


TEST_ETC_PATH = Path(__file__).parent / "etc"


# Test chain
def test_chunk_content():
    sample_content = """
    This is a test. It will split by double new line, new line, period, comma, spaces

    For example, new line it should split here
    When a sentence ends, it should be split here. If a comma appears it should be able to split here, If a space is used it should split here
    """

    sample_document = Document(page_content=sample_content)

    # Run the chunk_content function
    chunked_documents = chunk_content(sample_document, chunk_size=20, chunk_overlap=5)

    # Expected chunks
    expected_chunks = [
        "This is a test",
        ". It will split by double new line, new line, period, comma, spaces",
        "For example, new line it should split here",
        "When a sentence ends, it should be split here",
        ". If a comma appears it should be able to split here",
        ", If a space is used it should split here",
    ]

    # Compare the chunks
    for idx, doc in enumerate(chunked_documents):
        assert doc.page_content.strip() == expected_chunks[idx]


# Test hashers
def test_hash_string_simple():
    input_str = "hello"
    expected_output = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert hash_string(input_str) == expected_output


def test_hash_string_special_characters():
    input_str = "建築基準法施行令"
    expected_output = "44179010fc893672f9ac0cf12cb5b57b3f19e1f698bd88b001874388412bf3e9"
    assert hash_string(input_str) == expected_output


def test_hash_string_empty():
    input_str = ""
    expected_output = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert hash_string(input_str) == expected_output


def test_hash_string_numeric():
    input_str = "12345"
    expected_output = "5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5"
    assert hash_string(input_str) == expected_output


# Test load env
def test_load_env_vars():
    env = dotenv_values(dotenv_path=TEST_ETC_PATH / "test.env")
    env_vars = load_env_vars(TEST_ETC_PATH / "test.env")
    assert env_vars == env


def test_load_env_vars_missing():
    with pytest.raises(EnvironmentError) as excinfo:
        load_env_vars(TEST_ETC_PATH / "test_missing.env")
    assert "Missing required environment variables: ['VAR2']" in str(excinfo.value)
