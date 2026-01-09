"""
HTTP Client Singleton для API Gateway

Использует один httpx.AsyncClient для всех запросов с:
- Connection pooling
- Keep-alive
- Retry logic
- Timeout management
"""

import httpx
from typing import Optional


_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """
    Получить singleton HTTP client

    Клиент создается один раз при старте приложения и переиспользуется для всех запросов
    """
    global _http_client

    if _http_client is None:
        raise RuntimeError(
            "HTTP Client is not initialized, please call `init_http_client()` first."
        )
    return _http_client


async def init_http_client():
    """
    Инициализация HTTP client при старте приложения

    Connection pooling настройки:
    - max_connections: 100 одновременных соединений
    - max_keepalive_connections: 20 keep-alive соединений
    - keepalive_expiry: 30 секунд
    """

    global _http_client

    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,  # Timeout на установку соединения
                read=30.0,  # Timeout на чтение ответа
                write=10.0,  # Timeout на отправку данных
                pool=5.0,  # Timeout на получение соединения из пула
            ),
            limits=httpx.Limits(
                max_connections=100,  # Максимум соединений
                max_keepalive_connections=20,  # Максимум keep-alive соединений
            ),
            http2=False,  # HTTP/1.1 (можно включить HTTP/2 если нужно)
            follow_redirects=False,  # Не следовать редиректам автоматически
        )


async def close_http_client():
    """
    Закрытие HTTP client при остановке приложения
    """
    global _http_client

    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
