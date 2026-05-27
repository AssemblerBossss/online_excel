from fastapi import APIRouter, Request
from api_gateway.app.config import settings
from api_gateway.app.utils import proxy_request

router = APIRouter()


# Auth Service Endpoints
@router.api_route(
    "/auth/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Auth"],
    description="Перенаправляет все запросы к /auth/* в Auth Service",
)
async def proxy_auth(request: Request, path: str):
    """Проксирует /auth/* запросы к Auth Service"""
    return await proxy_request(
        request=request,
        target_url=settings.AUTH_SERVICE_URL,
        path=f"/auth/{path}",
    )


@router.api_route(
    "/users/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Auth", "Users"],
    description="Перенаправляет все запросы к /users/* в Auth Service",
)
async def proxy_users(request: Request, path: str):
    """Проксирует /users/* запросы к Auth Service"""
    return await proxy_request(
        request=request,
        target_url=settings.AUTH_SERVICE_URL,
        path=f"/users/{path}",
    )


@router.api_route(
    "/tables",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Tables"],
    summary="Прокси для таблиц (коллекция)",
    description="Перенаправляет запросы к /tables в Main Service",
)
@router.api_route(
    "/tables/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Tables"],
    summary="Прокси для таблиц (элемент)",
    description="Перенаправляет запросы к /tables/* в Main Service",
)
async def proxy_tables(request: Request, path: str = ""):
    """Проксирует /tables/* запросы к Main Service"""
    return await proxy_request(
        request=request,
        target_url=settings.MAIN_SERVICE_URL,
        path=f"/tables/{path}",
    )


@router.api_route(
    "/search",
    methods=["GET"],
    tags=["Search"],
    summary="Поиск",
    description="Перенаправляет поисковые запросы в Main Service",
)
async def proxy_search(request: Request):
    """Проксирует /search* запросы к Main Service"""
    query_string = request.url.query
    path = f"/search/?{query_string}" if query_string else "/search"
    return await proxy_request(
        request=request,
        target_url=settings.MAIN_SERVICE_URL,
        path=path,
    )


@router.api_route(
    "/data/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
    tags=["Data"],
    summary="Прокси для данных",
    description="Перенаправляет запросы к /data/* в Main Service",
)
async def proxy_data(request: Request, path: str):
    """Проксирует /data/* запросы к Main Service"""
    return await proxy_request(
        request=request,
        target_url=settings.MAIN_SERVICE_URL,
        path=f"/data/{path}",
    )


# @router.api_route(
#     "/categories/{path:path}",
#     methods=["GET", "POST", "PUT", "DELETE"],
# )
# async def proxy_categories(request: Request, path: str):
#     """Проксирует /categories/* запросы к Main Service"""
#     return await proxy_request(
#         request=request,
#         target_url=settings.MAIN_SERVICE_URL,
#         path=f"/categories/{path}",
#     )
