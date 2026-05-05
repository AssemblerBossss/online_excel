import logging
from fastapi import Request, status, FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class FileSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения размера загружаемых файлов.

    Проверяет заголовок Content-Length для POST, PUT и PATCH запросов.
    Если размер файла превышает максимально допустимый, возвращает ошибку 413.
    """

    def __init__(self, app: FastAPI, max_file_size: int):
        super().__init__(app)
        self.max_file_size = max_file_size

    async def dispatch(self, request: Request, call_next):

        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("Content-Length")
            if content_length:
                file_size = int(content_length)
                logger.info(
                    "File upload attempt: {} bytes, limit: {} bytes".format(
                        file_size, self.max_file_size
                    )
                )
                if file_size > self.max_file_size:
                    logger.warning(
                        "File size limit exceeded: {} > {} for endpoint: {}".format(
                            file_size, self.max_file_size, request.url.path
                        )
                    )

                    response = JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "detail": f"File too large. Maximum size is {self.max_file_size / (1024 * 1024):.1f} MB",
                            "max_size_mb": self.max_file_size / (1024 * 1024),
                            "actual_size_mb": file_size / (1024 * 1024),
                        },
                    )
                    return response
        response = await call_next(request)
        return response
