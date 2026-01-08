from fastapi import Request, HTTPException, status, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

from app.utils.jwt_handler import verify_jwt_token, extract_token_from_header


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware для проверки JWT токенов

    Применяется ко ВСЕМ запросам, кроме публичных endpoints.

    Публичные endpoints (не требуют токен):
    - POST /api/v1/auth/register
    - POST /api/v1/auth/login
    - POST /api/v1/auth/refresh
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
        "/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
    }

    async def dispatch(self, request: Request, call_next: Callable) ->  Response:
        if request.url.path in self.PUBLIC_PATHS:
            return call_next(request)

        authorization_header = request.headers.get("Authorization")
        token = extract_token_from_header(authorization_header)

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Проверяем токен ЛОКАЛЬНО
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
        except HTTPException as e:
            raise e

        response = await call_next(request)
        return response

