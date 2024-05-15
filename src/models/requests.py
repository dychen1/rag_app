from pydantic import BaseModel


class CreateEmbeddingsRequest(BaseModel):
    client: str
    project: str
    url: str
