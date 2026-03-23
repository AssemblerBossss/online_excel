import logging
import httpx
from fastapi import Request, Response, HTTPException

from api_gateway.app.utils.http_client import get_http_client

logger = logging.getLogger(__name__)


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
        HTTPException: Если backend недоступен
    """

    url = f"{target_url}{path}"
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    # Читаем body
    body = await request.body()

    client = get_http_client()

    try:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params,
        )

        logger.debug("Proxied: %s %s → %s", request.method, url, response.status_code)

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

    response_headers = dict(response.headers)
    response_headers["cache-control"] = "no-store"
    response_headers.pop("etag", None)

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )
