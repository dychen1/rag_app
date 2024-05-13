from fastapi import FastAPI, Depends
from pathlib import Path

from src.utils.env import load_env_vars
from src.routers import upload
from src.utils.minio import get_minio_client


env_path = Path(__file__).parent.parent / "etc" / ".env"
load_env_vars(str(env_path))


app = FastAPI()
app.include_router(upload.router, dependencies=[Depends(get_minio_client)])
