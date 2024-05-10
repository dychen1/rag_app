from pydantic import BaseModel


class UploadResponse(BaseModel):
    signed_urls: list[str]
    details: str
