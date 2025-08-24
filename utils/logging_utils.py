"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

CytoLens Logging Utilities
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

from core import config


def setup_logging() -> None:
    """
    Setup centralized logging with rotation for the entire application.
    Uses configuration from settings.
    """
    # Create log directory if it doesn't exist
    Path(config.settings.log_dir).mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.settings.log_level.upper()))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Format for all logs (includes task_id when present)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.settings.log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Main log file with everything (for debugging and full context)
    log_file = os.path.join(config.settings.log_dir, "cytolens.log")
    time_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when=config.settings.log_rotation_interval,
        interval=1,
        backupCount=config.settings.log_rotation_count,
        encoding="utf-8",
    )
    time_handler.setLevel(getattr(logging, config.settings.log_level.upper()))
    time_handler.setFormatter(formatter)
    root_logger.addHandler(time_handler)

    # Separate error log for monitoring and alerting
    # Production best practice: easier to monitor, integrate with alerting systems
    error_log_file = os.path.join(config.settings.log_dir, "cytolens_errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        filename=error_log_file,
        maxBytes=config.settings.log_max_bytes,
        backupCount=config.settings.log_backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Reduce noise from libraries
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Configure app-specific loggers
    logging.getLogger("cytolens").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    Use module's __name__ for consistency.
    """
    return logging.getLogger(name)
