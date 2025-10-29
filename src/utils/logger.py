import logging
import sys
from pathlib import Path


def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""

    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        logger.addHandler(handler)
        logger.addHandler(stream_handler)

    return logger
