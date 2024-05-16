import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore as LCPinecone
from langchain_openai import OpenAIEmbeddings
from functools import lru_cache
from pinecone import Index


@lru_cache(maxsize=8)
def get_lc_pinecone(index: Index, project: str) -> LCPinecone:
    # Automatically infers OPENAI_API_KEY from env vars
    embeddings = OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", ""))
    return LCPinecone(index=index, namespace=project, embedding=embeddings)


def chunk_content(
    content: Document, encoding_name: str = "cl100k_base", chunk_size: int = 8191, chunk_overlap: int = 100
) -> list[Document]:
    """
    Splits the content of a given document into smaller chunks based on specified separators and encoding.
    The separators used for splitting include newlines, spaces, punctuation marks, and other special characters.

    Args:
        content (Document): The input document to be split into chunks.
        encoding_name (str): Encoding used for tokenizing. Defaults to cl100k_base as it's used for 3rd gen OpenAI embedding models.
        chunk_size (int, optional): The maximum size of each chunk. Defaults to 8191 as it's the limit for 3rd gen OpenAI embedding models.
        chunk_overlap (int, optional): The number of characters that overlap between chunks. Defaults to 50, somewhat of an arbitrary choice.

    Returns:
        list[Document]: A list of chunked documents, each representing a portion of the original document content.

    Example:
        >>> from langchain.schema import Document
        >>> doc = Document(page_content="This is a long document that needs to be chunked.")
        >>> chunks = _chunk_content(doc)
        >>> for chunk in chunks:
        ...     print(chunk.page_content)
    """
    text_splitter = RecursiveCharacterTextSplitter(
        separators=[
            "\n\n",
            "\n",
            " ",
            ".",
            ",",
            "\u200b",  # Zero-width space
            "\uff0c",  # Fullwidth comma
            "\u3001",  # Ideographic comma
            "\uff0e",  # Fullwidth full stop
            "\u3002",  # Ideographic full stop
            "",
        ],
        add_start_index=True,  # To keep split char as metadata attribute "start_index"
    ).from_tiktoken_encoder(
        encoding_name=encoding_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    documents = text_splitter.split_documents([content])
    return documents
