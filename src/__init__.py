from pathlib import Path
from src.utils.load_env import load_env_vars
from src.utils.logger import init_logger


etc_path = Path(__file__).parent.parent / "etc"

# Init env
load_env_vars(str(etc_path / ".env"))

# Init logger
init_logger(file_path=etc_path / "logs")
