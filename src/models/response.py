from pydantic import BaseModel


class UploadResponse(BaseModel):
    signed_urls: list[str]
    details: str


class CreateEmbeddingsResponse(BaseModel):
    details: str
