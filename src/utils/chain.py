import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableSerializable
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate
from langchain_pinecone import PineconeVectorStore as LCPinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from functools import lru_cache
from pinecone import Index
from pathlib import Path
from pydantic.v1.types import SecretStr  # Langchain requires pydantic v1...

from src import ENV
from src.utils.logger import get_logger

ETC_PATH: Path = Path(__file__).parent.parent.parent / "etc"
logger = get_logger(ETC_PATH / "logs")


@lru_cache(maxsize=8)
def get_lc_pinecone(index: Index, project: str) -> LCPinecone:
    embeddings = OpenAIEmbeddings(api_key=SecretStr(ENV["OPENAI_API_KEY"]), model=ENV["EMBEDDING_MODEL"])
    return LCPinecone(index=index, namespace=project, embedding=embeddings)


def chunk_content(
    content: Document,
    chunk_size: int = int(ENV["CHUNK_SIZE"]),
    chunk_overlap: int = int(ENV["CHUNK_OVERLAP"]),
) -> list[Document]:
    """
    Splits the content of a given document into smaller chunks based on specified separators and encoding.
    The separators used for splitting include newlines, spaces, punctuation marks, and other special characters.
    Chunk size and overlap are set as env vars.

    Args:
        content (Document): The input document to be split into chunks.
        encoding_name (str): Encoding used for tokenizing. Defaults to cl100k_base as it's used for 3rd gen OpenAI embedding models.

    Returns:
        list[Document]: A list of chunked documents, each representing a portion of the original document content.
    """
    encoding = tiktoken.encoding_for_model(ENV["CHAT_MODEL"])
    text_splitter = RecursiveCharacterTextSplitter().from_tiktoken_encoder(
        encoding_name=encoding.name,
        separators=[
            "\n\n",
            "\n",
            ".",
            ",",
            " ",
            "\u200b",  # Zero-width space
            "\uff0c",  # Fullwidth comma
            "\u3001",  # Ideographic comma
            "\uff0e",  # Fullwidth full stop
            "\u3002",  # Ideographic full stop
            "",
        ],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    logger.debug(
        f"Chunking using encoding '{encoding.name}' with separators: {text_splitter._separators}, chunk_size: {text_splitter._chunk_size}, chunk_overlap: {text_splitter._chunk_overlap}"
    )

    documents = text_splitter.split_documents([content])
    return documents


@lru_cache(maxsize=124)
def create_rag_chain(
    index: Index,
    project: str,
    file_name: str,
    prompt_file: Path,
    prompt_inputs: tuple[str],  # Needs to be hashable for caching
    search_type: str = "similarity",
) -> RunnableSerializable:
    """
    Creates a retrieval-augmented generation (RAG) chain.

    Args:
        index (Index): The Pinecone index to use for retrieval.
        project (str): The name of the project.
        file_name (str): The name of the file to filter the search.
        prompt_file (Path): The path to the prompt file.
        prompt_inputs (tuple[str, ...]): The input variables for the prompt, must be hashable for caching.
        search_type (str): The type of search to perform. Default is "similarity".

    Returns:
        RunnableSerializable: The constructed RAG chain.

    This function performs the following steps:
    1. Retrieves the retriever using the specified index and project.
    2. Reads the prompt template from the specified file.
    3. Creates a language model object used in the chain.
    4. Constructs the RAG chain using the retriever, prompt template, and language model object.
    5. Returns the constructed RAG chain.
    """
    top_k = int(ENV["TOP_K"])
    retriever = get_lc_pinecone(index, project).as_retriever(
        search_type=search_type,
        search_kwargs={
            "k": top_k,
            "filter": {"name": file_name},
        },
    )
    logger.info(f"Fetched top {top_k} chunks for file '{file_name}'")

    with open(Path(__file__).parent.parent / "prompts" / prompt_file) as file:
        prompt = file.read()
        prompt_template = PromptTemplate(input_variables=list(prompt_inputs), template=prompt)

    llm = ChatOpenAI(
        api_key=SecretStr(ENV["OPENAI_API_KEY"]),
        model=ENV["CHAT_MODEL"],
        temperature=float(ENV["TEMPERATURE"]),
    )
    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: _combine_context(x["context"])))
        | prompt_template
        | llm
        | StrOutputParser()
    )

    return RunnableParallel({"context": retriever, "question": RunnablePassthrough()}).assign(
        answer=rag_chain_from_docs
    )  # type: ignore


def _combine_context(docs: list[Document]) -> str:
    """
    Combines the content of a list of documents into a single string for LLM injestion.
    """
    # TODO: Check token size of single string in case it's too big for LLM context window.
    return "\n\n".join(doc.page_content for doc in docs)
