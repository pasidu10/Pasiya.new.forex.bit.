"""
Logging configuration for the Telegram AI Trading Assistant.
"""
import sys
import os
from loguru import logger
from datetime import datetime
from pathlib import Path


def setup_logger(log_level: str = "INFO", log_file: str = "logs/bot.log"):
    """Configure the logger for the application."""
    # Remove default handler
    logger.remove()

    # Ensure log directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Console handler with color
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )

    # File handler for all logs
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        encoding="utf-8",
    )

    # File handler for errors only
    logger.add(
        log_file.replace(".log", "_errors.log"),
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="90 days",
        compression="gz",
        encoding="utf-8",
    )

    logger.info(f"Logger initialized with level {log_level}")
    return logger


def get_logger(name: str = None):
    """Get a logger instance."""
    if name:
        return logger.bind(name=name)
    return logger
