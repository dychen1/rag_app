from fastapi import FastAPI, Depends

from src.routers import upload, create_embeddings
from src.utils.clients import get_minio_client, get_pinecone_client


app = FastAPI()
app.include_router(upload.router, dependencies=[Depends(get_minio_client)])
app.include_router(create_embeddings.router, dependencies=[Depends(get_pinecone_client)])
