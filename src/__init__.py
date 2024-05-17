from pathlib import Path
from src.utils.load_env import load_env_vars


etc_path = Path(__file__).parent.parent / "etc"

# Init env
ENV = load_env_vars(str(etc_path / ".env"))
