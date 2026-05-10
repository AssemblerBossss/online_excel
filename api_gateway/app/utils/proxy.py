import logging
import httpx
from aiobreaker import CircuitBreakerError
from fastapi import Request, Response, HTTPException

from api_gateway.app.circuit_breaker import resolve_service, circuit_breaker_registry
from api_gateway.app.utils.http_client import get_http_client

logger = logging.getLogger(__name__)


async def _do_request(
    method: str,
    url: str,
    headers: dict,
    body: bytes,
    params,
) -> httpx.Response:
    """Выполнить HTTP запрос через singleton клиент."""
    client = get_http_client()
    return await client.request(
        method=method,
        url=url,
        headers=headers,
        content=body,
        params=params,
    )


async def proxy_request(
    request: Request,
    target_url: str,
    path: str,
) -> Response | None:
    """
    Проксирует запрос к backend сервису
    Использует singleton HTTP client для эффективного connection pooling.

    Args:
        request: Входящий FastAPI запрос
        target_url: URL целевого сервиса (http://auth_service:8001)
        path: Путь запроса (/api/v1/users/me/)
    Returns:
        Response от backend сервиса

    Raises:
        HTTPException 503: Если сервис недоступен или circuit открыт
        HTTPException 504: Если сервис не ответил вовремя
        HTTPException 502: Прочие сетевые ошибки
    """

    url = f"{target_url}{path}"
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    # Читаем body
    body = await request.body()

    client = get_http_client()

    service = resolve_service(target_url)
    breaker = circuit_breaker_registry.get_breaker(service)

    try:
        response = await breaker.call_async(
            _do_request,
            request.method,
            url,
            headers,
            body,
            request.query_params,
        )
        logger.debug("Proxied: %s %s → %s", request.method, url, response.status_code)

    except CircuitBreakerError:
        # Circuit открыт — сервис признан недоступным, не ждём таймаута
        logger.warning(
            "Circuit open for %s, rejecting request to %s", service.value, url
        )
        raise HTTPException(
            status_code=503,
            detail=f"Service temporarily unavailable: {service.value} circuit is open",
        )
    except httpx.TimeoutException as e:
        logger.error("Timeout proxying to %s: %s", url, str(e))
        raise HTTPException(
            status_code=504,
            detail=f"Gateway timeout: {target_url} took too long to respond",
        )

    except httpx.ConnectError as e:
        logger.error("Connection error to  %s: %s", url, str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: Cannot connect to {target_url}",
        )

    except httpx.RequestError as e:
        logger.error("Request error to %s: %s", url, str(e))
        raise HTTPException(
            status_code=502,
            detail=f"Bad gateway: Error communicating with {target_url}",
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers={
            **dict(response.headers),
            "cache-control": "no-store",
        },
    )
