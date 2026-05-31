import time
import logging
import uuid
from fastapi import Request
from h11 import Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования всех запросов"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]

        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_host": request.client.host if request.client else None,
                "event": "request_start",
            },
        )

        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000

            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time, 2),
                    "event": "request_end",
                },
            )

            return response

        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "process_time_ms": round(process_time, 2),
                    "event": "request_error",
                },
                exc_info=True,
            )
            raise
