import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def init_logger(
    level: str = "info",
    app_name: str = "app",
    file_path: Path = Path(__file__).parent.parent.parent / "etc" / "logs",
    file_limit: int = 1024 * 1024 * 50,
    rollover_limit: int = 10,
) -> logging.Logger:
    """
    Initializes a logger with rotating file handlers for both general logs and error-only logs.

    Args:
        level (str): The logging level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') - lower case acceptable.
        filename (str): The base name of the log files. General logs will be saved to 'app.log' and error logs to 'app_err.log'.
        file_limit (int): The maximum size of the log file in bytes before rotation occurs. Defaults 50MB.
        rollover_limit (int): The number of backup log files to keep before overwriting old files. Defaults 10 rollovers.

    Returns:
        None
    """
    logger = logging.getLogger(app_name)
    if logger.hasHandlers():
        return logger  # Logger is already initialized

    file_path.mkdir(parents=True, exist_ok=True)  # Ensure the file path exists before creating log files to dir

    format = "%(threadName)s - %(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
    logger.setLevel(level.upper())

    # Main log handler
    handler = RotatingFileHandler(
        filename=f"{str(file_path)}/{app_name}.log", maxBytes=file_limit, backupCount=rollover_limit
    )
    handler.setFormatter(logging.Formatter(format))
    logger.addHandler(handler)

    # Error log file handler
    err_only_handler = RotatingFileHandler(
        filename=f"{str(file_path)}/{app_name}_err.log", maxBytes=file_limit, backupCount=rollover_limit
    )
    err_only_handler.setFormatter(logging.Formatter(format))
    err_only_handler.addFilter(lambda record: record.levelno >= logging.ERROR)
    logger.addHandler(err_only_handler)

    return logger
