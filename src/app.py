from fastapi import FastAPI, Depends

from src.routers import upload, create_embeddings, query
from src.utils.clients import get_minio_client
from src.utils.middleware.auth import AuthMiddleware
from src import ENV

app = FastAPI()
app.add_middleware(AuthMiddleware, api_key=ENV["API_KEY"])
app.include_router(upload.router, dependencies=[Depends(get_minio_client)])
app.include_router(create_embeddings.router)
app.include_router(query.router)
