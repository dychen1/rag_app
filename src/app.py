from fastapi import FastAPI, Depends
from pathlib import Path

from src.utils.env import load_env_vars
from src.utils.logger import init_logger
from src.routers import upload
from src.utils.minio import get_minio_client

# Init env
env_path = Path(__file__).parent.parent / "etc" / ".env"
load_env_vars(str(env_path))

# Init logger
init_logger()

app = FastAPI()
app.include_router(upload.router, dependencies=[Depends(get_minio_client)])
