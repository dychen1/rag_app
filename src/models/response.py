from pydantic import BaseModel
from langchain_core.documents import Document


class UploadResponse(BaseModel):
    signed_urls: list[str]
    details: str


class CreateEmbeddingsResponse(BaseModel):
    details: str


class QueryResponse(BaseModel):
    answer: str
    context: list[str]
