import logging
import sys
import json
from datetime import datetime, UTC


class ServiceJsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()  # ВАЖНО
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "service": "auth_service",
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.name.startswith("sqlalchemy"):
            log_record["component"] = "database"
            if hasattr(record, "sql"):
                log_record["sql"] = record.sql

        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


def setup_service_logging():
    """Настройка JSON-логирования для API Gateway"""

    service_formatter_instance = ServiceJsonFormatter("auth_service")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(service_formatter_instance)

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

    return root_logger
