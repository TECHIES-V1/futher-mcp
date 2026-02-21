import logging
import json
import os
import time
from datetime import datetime
from typing import Dict, Any
from functools import wraps
import traceback


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for easier log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        extras = ["file_path", "operation", "duration_ms", "page_count", "chapter_count", "error_type", "error_details"]
        for key in extras:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }
        return json.dumps(payload, ensure_ascii=False, default=str)


class StructuredLogger:
    """Helper that adds context to every log entry."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log_with_context(self, level: int, message: str, **context: Any) -> None:
        extra = {k: v for k, v in context.items() if v is not None}
        self.logger.log(level, message, extra=extra)

    def info(self, message: str, **context: Any) -> None:
        self._log_with_context(logging.INFO, message, **context)

    def debug(self, message: str, **context: Any) -> None:
        self._log_with_context(logging.DEBUG, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        self._log_with_context(logging.WARNING, message, **context)

    def error(self, message: str, **context: Any) -> None:
        self._log_with_context(logging.ERROR, message, **context)


def setup_logger(level: str = "INFO", log_file: str = "further_mcp.log") -> logging.Logger:
    """Configure both structured file logging and readable console output."""

    base_dir = os.path.join(os.path.dirname(__file__), "..", "..")
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, log_file)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    structured = StructuredFormatter()
    console = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(structured)
    file_handler.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(console)
    stream_handler.setLevel(getattr(logging, level.upper()))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    return root_logger


def get_logger(name: str) -> StructuredLogger:
    """Return a structured logger instance"""

    return StructuredLogger(name)


def log_operation(operation_name: str):
    """Decorator that adds duration metadata to logs."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start = time.time()
            logger.info(f"Starting {operation_name}", operation=operation_name)
            try:
                return func(*args, **kwargs)
            finally:
                duration = round((time.time() - start) * 1000, 2)
                logger.info(f"Completed {operation_name}", operation=operation_name, duration_ms=duration)

        return wrapper

    return decorator


# ensure we have a default logger configuration upon import
setup_logger()
