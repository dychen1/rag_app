from pathlib import Path
from src.utils.load_env import load_env_vars
from src.utils.logger import init_logger

# Init env
env_path = Path(__file__).parent.parent / "etc" / ".env"
load_env_vars(str(env_path))

# Init logger
init_logger()
