import logging
import sys
import json
from datetime import datetime


class ServiceJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "table_service",  # или "auth_service"
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Добавляем SQL запросы если есть
        if hasattr(record, "sql"):
            log_record["sql"] = record.sql

        return json.dumps(log_record, ensure_ascii=False)


def setup_service_logging(service_name: str):
    # Отключаем стандартные логи SQLAlchemy
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ServiceJsonFormatter())

    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    return root_logger
