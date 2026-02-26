from fastapi import APIRouter, Request
from api_gateway.app.config import settings
from api_gateway.app.utils import proxy_request

router = APIRouter()


# Auth Service Endpoints
@router.api_route(
    "/auth/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_auth(request: Request, path: str):
    """
    Проксирует /auth/* запросы к Auth Service
    """
    user_data = None
    if hasattr(request.state, "user"):
        user_data = request.state.user

    return await proxy_request(
        request=request,
        target_url=settings.AUTH_SERVICE_URL,
        path=f"/auth/{path}",
        user_data=user_data,
    )


@router.api_route(
    "/users/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_users(request: Request, path: str):
    """
    Проксирует /users/* запросы к Auth Service

    Примеры:
    - GET /api/users/me/ → Auth Service
    - GET /api/users/123 → Auth Service
    """
    user_data = None
    if hasattr(request.state, "user"):
        user_data = request.state.user

    return await proxy_request(
        request=request,
        target_url=settings.AUTH_SERVICE_URL,
        path=f"/users/{path}",
        user_data=user_data,
    )


# Main Service Endpoints


@router.api_route(
    "/tables",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
@router.api_route(
    "/tables/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_tables(request: Request, path: str = ""):
    """
    Проксирует /tables/* запросы к Main Service
    """
    user_data = None
    if hasattr(request.state, "user"):
        user_data = request.state.user

    return await proxy_request(
        request=request,
        target_url=settings.MAIN_SERVICE_URL,
        path=f"/tables/{path}",
        user_data=user_data,
    )


@router.api_route(
    "/categories/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
)
async def proxy_categories(request: Request, path: str):
    """
    Проксирует /categories/* запросы к Main Service
    """
    user_data = None
    if hasattr(request.state, "user"):
        user_data = request.state.user

    return await proxy_request(
        request=request,
        target_url=settings.MAIN_SERVICE_URL,
        path=f"/categories/{path}",
        user_data=user_data,
    )


@router.api_route(
    "/data/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
)
async def proxy_categories(request: Request, path: str):
    """
    Проксирует /data/* запросы к Main Service
    """
    user_data = None
    if hasattr(request.state, "user"):
        user_data = request.state.user

    return await proxy_request(
        request=request,
        target_url=settings.MAIN_SERVICE_URL,
        path=f"/data/{path}",
        user_data=user_data,
    )
