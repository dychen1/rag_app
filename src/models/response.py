from pydantic import BaseModel
from langchain_core.documents import Document


class UploadResponse(BaseModel):
    signed_urls: list[str]
    details: str


class CreateEmbeddingsResponse(BaseModel):
    ids: list[str]
    timestamp: int
    file_name: str
    details: str


class QueryResponse(BaseModel):
    answer: str
    context: list[str]
