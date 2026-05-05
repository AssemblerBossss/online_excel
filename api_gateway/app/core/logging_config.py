import logging
from typing import Any
from datetime import datetime, UTC
import json


class CustomJsonFormatter(logging.Formatter):
    """Кастомный JSON форматер для логов"""

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "level": record.levelname,
            "service": "api_gateway",
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


import sys
import logging


def setup_logging():
    """Настройка JSON-логирования для API Gateway"""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomJsonFormatter())

    # --- Root logger ---
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # --- Uvicorn loggers ---
    for logger_name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    # Если не нужен access log — просто отключаем
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True

    # --- Убираем спам от httpx ---
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return root_logger
