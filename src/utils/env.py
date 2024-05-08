import os
from pathlib import Path

from dotenv import load_dotenv


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
    env_path = Path(env_file)
    load_dotenv(dotenv_path=env_path)

    required_vars = ["MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var, "").strip()]
    if missing_vars:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")
