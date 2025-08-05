import logging

import os

logger = logging.getLogger("sharepoint_api")


def configure_logging(level=logging.INFO, log_file=None, log_format=None):
    """
    Configure the logging for the SharePoint API module.

    Args:
        level: The logging level (default: logging.INFO)
        log_file: Optional file path to write logs to
        log_format: Optional custom log format
    """
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Configure the logger
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates when reconfigured
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create file handler if log_file specified
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.debug("SharePoint API logging configured")
