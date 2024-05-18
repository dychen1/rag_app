import aiofiles
import json
import os
import sys
import time
from aiohttp import ClientSession
from fastapi import HTTPException, APIRouter
from datetime import datetime
from datetime import timezone
from langchain_core.documents import Document
from pathlib import Path
from pinecone import Index
from urllib.parse import urlparse, unquote

from src.models.requests import CreateEmbeddingsRequest
from src.models.response import CreateEmbeddingsResponse
from src.utils.decorators import async_retry
from src.utils.logger import get_logger
from src.utils.clients import get_pinecone_index
from src.utils.hashers import hash_string
from src.utils.chain import get_lc_pinecone, chunk_content

ETC_PATH: Path = Path(__file__).parent.parent.parent / "etc"
router = APIRouter()
logger = get_logger(file_path=ETC_PATH / "logs")

# Ensure tmp download path is created
TMP_PATH: Path = ETC_PATH / "tmp"
TMP_PATH.mkdir(parents=True, exist_ok=True)
PARTIAL_SUFFIX: str = ".part"


@router.post("/create_embeddings")
async def create_embeddings(
    request: CreateEmbeddingsRequest,
) -> CreateEmbeddingsResponse:
    """
    Endpoint to create and store embeddings for a document fetched from a given URL.

    Args:
        request (CreateEmbeddingsRequest): Request object containing the URL of the document to be processed, along with client and project information.

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
    await _download_file(request.url, file_path)

    # Run mock OCR and produce langchain Document
    full_content: Document = await _mock_ocr_extraction(file_name)

    # Clean up tmp space
    os.remove(file_path)
    logger.debug(f"Cleaned up/deleted {file_path}.")

    # Chunk ORC output with langchain, supports Japanese punctuation when chunking
    documents: list[Document] = chunk_content(full_content)
    logger.info(f"Split content into {len(documents)} documents.")

    # Add metadata to documents and generate ids for vectors manually
    ids: list[str] = []
    for idx, doc in enumerate(documents):
        doc.metadata = {"name": file_name, "chunk_id": idx, "timestamp": timestamp}
        ids.append(hash_string(f"{idx}_{file_name}"))  # Hash ids so that we can represent doc name in ASCII
    logger.debug(f"Generated {len(ids)} id's for documents chunks: {ids}.")

    # Get pinecone index, create if it doesnt exist for client
    index = await get_pinecone_index(request.client)

    # Upload embeddings to vector db
    await _upload_to_pinecone(index, request.client, request.project, documents, ids)

    return CreateEmbeddingsResponse(
        ids=ids,
        timestamp=timestamp,
        file_name=file_name,
        details=f"Sucessfully added document to vector store under index '{request.client}' with namespace '{request.project}'",
    )


@async_retry(logger, max_attempts=3, initial_delay=1, backoff_base=2)
async def _download_file(url: str, download_path: Path) -> None:
    """
    Downloads a file from the given URL and saves it to disk, supporting resumable downloads.

    Args:
        url (str): The URL to download the file from.
        download_path (str): The path and file name of the file.

    Raises:
        HTTPException: If the response status is not successful.
    """

    async def _incremental_download(session: ClientSession, url: str, download_path: Path) -> None:
        partial_file: Path = download_path.with_suffix(PARTIAL_SUFFIX)
        mode: str = "wb" if not partial_file.exists() else "ab"
        existing_size: int = partial_file.stat().st_size if partial_file.exists() else 0
        headers: dict[str, str] = {"Range": f"bytes={existing_size}-"} if existing_size else {}

        async with session.get(url, headers=headers) as response:
            response.raise_for_status()

            async with aiofiles.open(partial_file, mode) as f:
                async for chunk in response.content.iter_chunked(1024 * 10):  # Reads response in 10KB chunks
                    await f.write(chunk)
                    await f.flush()

        partial_file.rename(download_path)  # Remove .part suffix when download is complete

    async with ClientSession() as session:
        try:
            logger.debug(f"Downloading to {download_path}.")

            start = time.time()
            await _incremental_download(session, url, download_path)
            file_size: float = round(os.path.getsize(download_path) / 1024, 2)  # File size in KB

            logger.info(f"Downloaded file of size {file_size}KB in {round(time.time()-start, 2)}s.")
        except HTTPException as e:
            msg = f"Failed to download file from url: {e}"
            logger.error(msg)
            raise HTTPException(status_code=500, detail=msg)


async def _mock_ocr_extraction(file_name: str) -> Document:
    """
    Mock function to extract OCR content from a specified PDF file.

    Args:
        file_path (Path): Path object to file for which OCR content is to be extracted.

    Returns:
        Document: A Document object containing the OCR-extracted text from the specified file.

    Notes:
        - This function currently supports only specific sample files.
        - The OCR content is loaded from corresponding JSON files in the 'ocr_samples' directory.
    """
    # TODO: Incremental loading of OCR output as to not load all content of document into mem all at once
    samples_path = ETC_PATH / "ocr_samples"
    try:
        if file_name == "建築基準法施行令.pdf":
            with open(samples_path / "建築基準法施行令.json") as file:
                data = json.load(file)
                content = data["analyzeResult"]["content"]

        elif file_name == "東京都建築安全条例.pdf":
            with open(samples_path / "東京都建築安全条例.json") as file:
                data = json.load(file)
                content = data["analyzeResult"]["content"]

        elif str(file_name).endswith(".txt"):  # For testing convenience
            with open(ETC_PATH / "sample_files" / file_name) as file:
                content = file.read()

        else:
            content = ""  # Only supporting sample files for now

        logger.info(f"Size of content from {file_name}: {round(sys.getsizeof(content)/1024, 2)}KB")
    except MemoryError:
        logger.error(f"Not enough memory for file of size {round(os.path.getsize(file_name) / 1024 / 1024, 4)}MB")

    return Document(page_content=content)


@async_retry(logger=logger, max_attempts=3, initial_delay=1, backoff_base=2)
async def _upload_to_pinecone(
    index: Index, client: str, project: str, documents: list[Document], ids: list[str]
) -> None:
    """
    Internal function to upload documents to a Pinecone index with retries in case of failures.

    Args:
        index (Index): Pinecone index to which the documents will be uploaded.
        client (str): Client/index name associated with the upload.
        project (str): Project name/namespace associated with the upload.
        documents (list[Document]): List of chunked documents to upload.
        ids (list[str]): The list of IDs corresponding to the documents in order.
    """
    start = time.time()
    lc_pinecone = get_lc_pinecone(index, project)
    await lc_pinecone.aadd_documents(documents=documents, ids=ids)  # Adds chunked documents with upsert async

    logger.info(
        f"Took {round(time.time()-start, 2)}s to embed and upsert documents to index: '{client}' namespace: '{project}'."
    )
