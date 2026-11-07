import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "prism.log"

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)


def get_logger(name: str) -> logging.Logger:
    """Create and configure a production-grade logger with console and rotating file outputs."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)

    # 1. Console Handler (always available - streams to stderr so stdout is clean for MCP JSON-RPC stdio)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Rotating File Handler (with graceful degradation for read-only environments)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError, PermissionError:
        # Read-only filesystem or restricted permissions; continue with console logging
        pass

    logger.propagate = False
    return logger


if __name__ == "__main__":
    logger = get_logger(__name__)

    logger.info("PRISM logger started")
    logger.warning("Logger warning test")
    logger.error("Logger error test")
