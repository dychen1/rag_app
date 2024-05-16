from fastapi import APIRouter
from pathlib import Path
from langchain_core.documents import Document

from src.models.response import QueryResponse
from src.models.requests import QueryRequest
from src.utils.logger import init_logger
from src.utils.chain import create_rag_chain
from src.utils.clients import get_pinecone_index

router = APIRouter()
logger = init_logger(file_path=Path(__file__).parent.parent.parent / "etc" / "logs")


@router.post("/query")
async def query(request: QueryRequest) -> QueryResponse:
    """
    Handles a query request, invokes a retrieval-augmented generation (RAG) chain to provide an answer.

    Args:
        request (QueryRequest): The query request containing the client, project, file name, and query string.

    Returns:
        QueryResponse: The response containing the answer and the context used to generate the answer.

    Raises:
        TypeError: If the response does not contain the expected types for 'answer' and 'context'.

    This function performs the following steps:
    1. Retrieves the Pinecone index which serves as a connection using the provided client information.
    2. Creates a RAG chain using the retrieved index, project name, file name, and a prompt file.
    3. Invokes the chain with the query provided in the request.
    4. Extracts the answer and context from the response.
    5. Returns a QueryResponse object with the answer and context.
    """
    index = await get_pinecone_index(client=request.client)
    chain = create_rag_chain(
        index=index,
        project=request.project,
        file_name=request.file_name,
        prompt_file=Path("query_prompt.txt"),
        prompt_inputs=("context", "question"),
    )
    logger.debug(f"Chain created: {chain}")
    response: dict[str, list[Document] | str] = chain.invoke(request.query)
    if isinstance(response["answer"], str) and isinstance(response["context"], list):
        answer: str = response["answer"]
        context: list[str] = [doc.page_content for doc in response["context"]]
    else:
        raise TypeError(
            f"Response does not contain expected types - answer:{type(response['answer'])}, context: {type(response['context'])}"
        )
    logger.debug(f"LLM answer:\n{answer}")
    logger.debug(f"Context used:\n{context}")
    return QueryResponse(answer=answer, context=context)
