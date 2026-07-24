from fastapi import Request
from slowapi import Limiter

from auth_service.app.config import auth_service_settings


def get_client_ip(request: Request) -> str:
    """Извлечение IP-адреса клиента из запроса."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=auth_service_settings.REDIS_URL,
    strategy="fixed-window",
    enabled=True,
    headers_enabled=True,
)
