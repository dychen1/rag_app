import aiofiles
import json
import os
import sys
import time
from aiohttp import ClientSession
from fastapi import HTTPException, APIRouter, Depends
from datetime import datetime
from datetime import timezone
from functools import lru_cache
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore as LCPinecone
from langchain_openai import OpenAIEmbeddings
from pathlib import Path
from pinecone import Pinecone, ServerlessSpec
from urllib.parse import urlparse, unquote

from src.models.requests import CreateEmbeddingsRequest
from src.models.response import CreateEmbeddingsResponse
from src.utils.decorators import async_retry
from src.utils.logger import init_logger
from src.utils.clients import get_pinecone_client
from src.utils.hashers import hash_string


ETC_PATH: Path = Path(__file__).parent.parent.parent / "etc"
router = APIRouter()
logger = init_logger(file_path=ETC_PATH / "logs")

# Ensure tmp download path is created
TMP_PATH: Path = ETC_PATH / "tmp"
TMP_PATH.mkdir(parents=True, exist_ok=True)
PARTIAL_SUFFIX: str = ".part"

EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "")  # Should never default to "" as it's a required var
DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}  # Dimensions per model, currently only set up for OpenAI embedding models


@router.post("/create_embeddings")
async def create_embeddings(
    request: CreateEmbeddingsRequest,
    pinecone_client=Depends(get_pinecone_client),
) -> CreateEmbeddingsResponse:
    """
    Endpoint to create and store embeddings for a document fetched from a given URL.

    Args:
        request (CreateEmbeddingsRequest): Request object containing the URL of the document to be processed, along with client and project information.
        pinecone_client (Depends): Dependency injection for the Pinecone client.

    Returns:
        CreateEmbeddingsResponse: Response object containing details of the operation.

    Workflow:
        1. Downloads the file from the specified URL.
        2. Runs a mock OCR extraction on the downloaded file to produce a langchain Document.
        3. Cleans up by deleting the downloaded file from the temporary storage.
        4. Splits the OCR output into smaller chunks.
        5. Adds metadata to each chunk and generates unique IDs for the vectors.
        6. Checks if a Pinecone index exists for the client; if not, creates one for the client.
        7. Uploads the embeddings to the vector database.
    """
    # Set file path
    # Epoch time in microseconds to minimize race condition when two files with same name are downloaded at the same time
    timestamp: int = int(datetime.now(timezone.utc).timestamp() * 10**6)
    file_name: str = unquote(str(os.path.basename(urlparse(request.url).path)))
    stamped_file_name = str(timestamp) + "_" + file_name
    file_path: Path = TMP_PATH / stamped_file_name

    # Download file to disk
    async with ClientSession() as session:
        try:
            logger.debug(f"Downloading to {file_path}.")
            start = time.time()
            await _download_file(session, request.url, file_path)
            file_size: float = round(os.path.getsize(file_path) / 1024, 2)  # File size in KB
            logger.info(f"Downloaded file of size {file_size}KB in {round(time.time()-start, 2)}s.")
        except HTTPException as e:
            msg = f"Failed to download file from url: {e}"
            logger.error(msg)
            raise HTTPException(status_code=500, detail=msg)

    # Run mock OCR and produce langchain Document
    try:
        full_content: Document = await _mock_ocr_extraction(file_name)
    except MemoryError:
        logger.error(f"File of size {file_size}KB")

    # Clean up tmp space
    logger.debug(f"Cleaning up/deleting {file_path}.")
    os.remove(file_path)

    # Chunk ORC output with langchain, supports Japanese punctuation when chunking
    documents: list[Document] = _chunk_content(full_content)
    logger.info(f"Split content into {len(documents)} documents.")

    # Add metadata to documents and generate ids for vectors manually
    ids: list[str] = []
    for idx, doc in enumerate(documents):
        doc.metadata = {"name": file_name, "chunk_id": idx, "timestamp": timestamp}
        ids.append(hash_string(f"{idx}_{file_name}"))  # Hash ids so that we can represent doc name in ASCII
    logger.debug(f"Generated {len(ids)} id's for documents chunks: {ids}.")

    # Check pinecone for index, create if it doesnt exist for client
    _check_pinecone_index(request.client, pinecone_client)

    # Upload embeddings to vector db
    try:
        start = time.time()
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)  # Automatically infers OPENAI_API_KEY from env vars
        lc_pinecone = LCPinecone(index_name=request.client, namespace=request.project, embedding=embeddings)
        await lc_pinecone.aadd_documents(documents=documents, ids=ids)  # Adds chunked documents with upsert async
        logger.info(
            f"Took {round(time.time()-start, 2)}s to embed and upsert documents to index: '{request.client}' namespace: '{request.project}'."
        )
    except Exception as e:  # TODO: Change catch all
        msg = f"Error when upserting documents to index: '{request.client}' namespace: '{request.project}':\n{e}"
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)

    return CreateEmbeddingsResponse(
        details=f"Sucessfully added document {file_name} to vector store under index '{request.client}' with namespace '{request.project}'"
    )


@async_retry(logger, max_attempts=3, initial_delay=1, backoff_factor=2)
async def _download_file(session: ClientSession, url: str, file_path: Path) -> None:
    """
    Downloads a file from the given URL and saves it to disk, supporting resumable downloads.

    Args:
        session (ClientSession): The aiohttp client session used for making HTTP requests.
        url (str): The URL to download the file from.
        file_path (str): The path and file name of the file.

    Raises:
        HTTPException: If the response status is not successful.
    """
    partial_file: Path = file_path.with_suffix(PARTIAL_SUFFIX)
    mode: str = "wb" if not partial_file.exists() else "ab"
    existing_size: int = partial_file.stat().st_size if partial_file.exists() else 0
    headers: dict[str, str] = {"Range": f"bytes={existing_size}-"} if existing_size else {}

    async with session.get(url, headers=headers) as response:
        response.raise_for_status()

        async with aiofiles.open(partial_file, mode) as f:
            async for chunk in response.content.iter_chunked(1024 * 10):  # Reads response in 10KB chunks
                await f.write(chunk)
                await f.flush()

    partial_file.rename(file_path)  # Remove .part suffix when download is complete


async def _mock_ocr_extraction(file_name: str) -> Document:
    """
    Mock function to extract OCR content from a specified PDF file.

    Args:
        file_name (str): The name of the PDF file for which OCR content is to be extracted.

    Returns:
        Document: A Document object containing the OCR-extracted text from the specified PDF file.

    Notes:
        - This function currently supports only specific sample files.
        - The OCR content is loaded from corresponding JSON files in the 'ocr_samples' directory.
    """
    # TODO: Incremental loading of OCR output as to not load all content of document into mem all at once
    samples_path = ETC_PATH / "ocr_samples"
    if file_name == "建築基準法施行令.pdf":
        with open(samples_path / "建築基準法施行令.json") as file:
            data = json.load(file)
            content = data["analyzeResult"]["content"]

    elif file_name == "東京都建築安全条例.pdf":
        with open(samples_path / "東京都建築安全条例.json") as file:
            data = json.load(file)
            content = data["analyzeResult"]["content"]

    else:
        content = ""  # Only supporting sample files for now

    logger.info(f"Size of content from {file_name}: {round(sys.getsizeof(content)/1024, 2)}KB")
    return Document(page_content=content)


def _chunk_content(
    content: Document, encoding_name: str = "cl100k_base", chunk_size: int = 8191, chunk_overlap: int = 50
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
        ]
    ).from_tiktoken_encoder(
        encoding_name=encoding_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    documents = text_splitter.split_documents([content])
    return documents


@lru_cache(maxsize=8)  # Can increase cache size if we have more indexes
def _check_pinecone_index(
    client: str,
    pinecone_client: Pinecone,
    dimension: int | None = None,
    metric: str = "cosine",
    cloud: str = "aws",
    region: str = "us-east-1",
) -> None:
    """
    Creates a Pinecone index if it doesn't already exist.

    Args:
        client (str): Name of the index.
        pinecone_client (Pinecone): Pinecone client used to connect to index.
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

    # TODO: Handle case where index is deleted on the host while it's still cached in app
