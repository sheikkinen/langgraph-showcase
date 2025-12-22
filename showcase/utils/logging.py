"""Structured logging configuration for the showcase app.

Provides consistent logging across all modules with JSON-formatted
output for production environments.
"""

import logging
import os
import sys
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured log messages.
    
    In production (LOG_FORMAT=json), outputs JSON lines.
    In development, outputs human-readable format.
    """
    
    def __init__(self, use_json: bool = False):
        super().__init__()
        self.use_json = use_json
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record."""
        if self.use_json:
            import json
            log_data = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            # Add extra fields if present
            if hasattr(record, "extra"):
                log_data.update(record.extra)
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_data)
        else:
            # Human-readable format
            base = f"{self.formatTime(record)} [{record.levelname}] {record.name}: {record.getMessage()}"
            if record.exc_info:
                base += f"\n{self.formatException(record.exc_info)}"
            return base


def setup_logging(
    level: str | None = None,
    use_json: bool | None = None,
) -> logging.Logger:
    """Configure logging for the showcase app.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). 
               Defaults to LOG_LEVEL env var or INFO.
        use_json: If True, output JSON lines. 
                  Defaults to LOG_FORMAT=json env var.
    
    Returns:
        Root logger for the showcase package
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    
    if use_json is None:
        use_json = os.getenv("LOG_FORMAT", "").lower() == "json"
    
    # Get the showcase logger
    logger = logging.getLogger("showcase")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Add handler with formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(StructuredFormatter(use_json=use_json))
    logger.addHandler(handler)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started", extra={"topic": "AI"})
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Log a message with additional context fields.
    
    Args:
        logger: Logger instance
        level: Log level (logging.INFO, etc.)
        message: Log message
        **context: Additional context fields
        
    Example:
        >>> log_with_context(logger, logging.INFO, "Node completed", 
        ...                  node="generate", duration=1.5)
    """
    extra = {"extra": context} if context else {}
    logger.log(level, message, extra=extra)


# Initialize logging on import
_root_logger = setup_logging()
