from fastapi import Request, HTTPException, status, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import URL
from typing import Callable
from logging import getLogger

from api_gateway.app.utils import verify_jwt_token, extract_token_from_header


logger = getLogger(__name__)


def _normalize_path(request: Request, original_path: str, normalized_path: str) -> None:
    """Нормализует путь запроса"""

    new_url = str(request.url).replace(original_path, normalized_path, 1)
    request.scope["path"] = normalized_path
    request.scope["raw_path"] = normalized_path.encode()
    request._url = URL(new_url)

    # Обновляем путь в scope для дальнейшей обработки
    request.scope["path"] = normalized_path
    request.scope["raw_path"] = normalized_path.encode()


def _check_authorization(request: Request) -> JSONResponse | None:
    authorization_header = request.headers.get("Authorization")
    token = extract_token_from_header(authorization_header)

    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing authorization header"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверяем токен
    try:
        user_data = verify_jwt_token(token)

        # Сохраняем данные пользователя в request state
        # Это будет использоваться в proxy для добавления headers
        request.state.user = {
            "user_id": user_data.user_id,
            "email": user_data.email,
            "role": user_data.role,
            "is_active": user_data.is_active,
        }

    except HTTPException as exc:
        # Преобразуем HTTPException в JSONResponse
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers or {"WWW-Authenticate": "Bearer"},
        )

    except Exception as exc:
        # Логируем неожиданные ошибки при проверке токена
        logger.error(f"Error verifying token: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware для проверки JWT токенов

    Применяется ко ВСЕМ запросам, кроме публичных endpoints.

    Публичные endpoints (не требуют токен):
    - POST /api/auth/register
    - POST /api/auth/login
    - POST /api/auth/refresh
    - GET /health
    - GET /

    Для защищенных endpoints:
    1. Извлекает токен из Authorization header
    2. Проверяет JWT локально (verify_jwt_token)
    3. Сохраняет данные пользователя в request.state.user
    4. Передает запрос дальше (к proxy)
    """

    PUBLIC_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/health",
        "/openapi.json",
        "/favicon.ico",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/refresh",
        "/api/auth/logout",
    }

    async def dispatch(self, request: Request, call_next: Callable) ->  Response:
        original_path = request.url.path
        normalized_path = original_path.rstrip('/')

        # Если путь изменился - создаем новый request с нормализованным путем
        if original_path != normalized_path and normalized_path:
            _normalize_path(request=request, original_path=original_path, normalized_path=normalized_path)

        # Проверка публичных путей
        if normalized_path in self.PUBLIC_PATHS:
            return await call_next(request)

        auth_result = _check_authorization(request)
        if isinstance(auth_result, JSONResponse):
            return auth_result

        # Продолжаем обработку запроса
        response = await call_next(request)
        return response
