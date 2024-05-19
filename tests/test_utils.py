from langchain_core.documents import Document

from src.utils.chain import chunk_content


def test_chunk_content():
    # Create a sample Document object that includes spaces, periods, commas, and the special characters
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
