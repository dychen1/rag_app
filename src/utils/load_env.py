import os
from pathlib import Path

from dotenv import load_dotenv


REQUIRED_VARS: list[str] = [
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "MINIO_VOLUMES",
    "MINIO_HOSTNAME",
    "MINIO_API_PORT",
    "OPENAI_API_KEY",
    "PINECONE_API_KEY",
    "EMBEDDING_MODEL",
]


def load_env_vars(env_file: str) -> None:
    """
    Load environment variables from a specified .env file and validate them.

    This function checks that certain required environment variables are both present
    and non-empty. If any required variables are missing or empty, an error is raised.

    Parameters:
        env_file (str): The file path to the .env file.

    Returns:
        dict[str, str]: A dictionary of the environment variables and their values.

    Raises:
        EnvironmentError: If any required environment variables are missing or empty.
    """
    load_dotenv(dotenv_path=Path(env_file))

    missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var, "").strip()]
    if missing_vars:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")
