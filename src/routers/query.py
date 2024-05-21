from pathlib import Path

from fastapi import APIRouter, HTTPException
from langchain_core.documents import Document
from openai import AuthenticationError
from pinecone.exceptions import UnauthorizedException

from src.models.requests import QueryRequest
from src.models.response import QueryResponse
from src.utils.chain import create_rag_chain
from src.utils.clients import get_pinecone_index
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(file_path=Path(__file__).parent.parent.parent / "etc" / "logs")


@router.post("/query")
async def query(request: QueryRequest) -> QueryResponse:
    """
    Handles a query request, invokes a retrieval-augmented generation (RAG) chain to provide an answer.

    Args:
        request (QueryRequest): The query request containing the client, project, file name, and query string.

    Returns:
        QueryResponse: The response containing the answer and the context used to generate the answer.

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
    # Run chain
    try:
        response: dict[str, list[Document] | str] = chain.invoke(request.query)
    except UnauthorizedException:
        raise HTTPException(status_code=401, detail=f"Unauthorized key for Pinecone index for client {request.client}.")
    except AuthenticationError:
        raise HTTPException(status_code=401, detail=f"Unauthorized key for OpenAI API.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)

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
