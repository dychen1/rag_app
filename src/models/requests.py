from pydantic import BaseModel


class CreateEmbeddingsRequest(BaseModel):
    client: str
    project: str
    url: str


class QueryRequest(BaseModel):
    client: str
    project: str
    file_name: str
    query: str
