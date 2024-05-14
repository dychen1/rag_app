from fastapi import FastAPI, Depends

from src.routers import upload
from src.utils.minio import get_minio_client


app = FastAPI()
app.include_router(upload.router, dependencies=[Depends(get_minio_client)])
