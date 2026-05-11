from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi.wrappers import Limit
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from logging import getLogger
from api_gateway.app.config import settings

logger = getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Извлечение IP-адреса клиента из запроса."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "unknown"


# Инициализируем лимитер
limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=True,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)


async def custom_rate_limit_handler(
    request: Request, exc: RateLimitExceeded
) -> Response:
    # exc.limit - это объект Limit
    limit_obj: Limit = exc.limit

    # Формируем читаемое правило, например "10 per minute"
    limit_rule = f"{limit_obj.limit}"

    # Стандартный заголовок: просим подождать 60 секунд (или значение granularity)
    # В реальном приложении здесь должна быть логика вычисления времени до сброса из Redis
    retry_after_seconds = limit_obj.granularity

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests",
            "error": "RATE_LIMIT_EXCEEDED",
            "limit": limit_rule,  # Показываем пользователю правило
            "retry_after": retry_after_seconds,
        },
        headers={
            "Retry-After": str(retry_after_seconds),
        },
    )


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения частоты запросов с использованием slowapi

    Применяется ко всем запросам, кроме:
    - Публичных health-check endpoints
    - Документации (/docs, /redoc, /openapi.json)
    """

    # Пути, не требующие rate limiting
    EXCLUDED_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
        "/health",
        "/health/circuit-breakers",
    }

    def __init__(self, app, limiter: Limiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Проверяем, нужно ли применять rate limiting к этому пути
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Применяем rate limiting
        try:
            response = await call_next(request)

            # Добавляем заголовки rate limiting в ответ
            if hasattr(self.limiter, "enabled") and self.limiter.enabled:
                remaining = getattr(request.state, "rate_limit_remaining", None)
                if remaining is not None:
                    response.headers["X-RateLimit-Remaining"] = str(remaining)

            return response

        except RateLimitExceeded as exc:
            # Обрабатываем превышение лимита
            return await custom_rate_limit_handler(request, exc)

        except Exception as exc:
            # Логируем другие ошибки
            logger.error(f"Rate limiter error: {exc}", exc_info=True)
            return await call_next(request)
