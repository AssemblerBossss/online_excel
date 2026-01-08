import time
import logging
from fastapi import Request
from h11 import Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования всех запросов
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        logger.info("[RequestLoggingMiddleware] Incoming {} {}".format(request.method, request.url))

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"Completed: {request.method} {request.url.path} "
            f"Status: {response.status_code} Time: {process_time:.3f}s"
        )

        # Добавляем header с временем обработки
        response.headers["X-Process-Time"] = str(process_time)

        return response