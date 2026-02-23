import sys
import logging
from typing import Any
from datetime import datetime
import json


class CustomJsonFormatter(logging.Formatter):
    """Кастомный JSON форматер для логов"""

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now().isoformat() + "Z",
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


def setup_logging():
    """Настройка логирования для API Gateway"""

    # Убираем стандартные хендлеры uvicorn
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = False

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Создаем хендлер для stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomJsonFormatter())

    # Добавляем хендлер к корневому логгеру
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Настраиваем логгер для httpx (чтобы не было спама)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return root_logger
