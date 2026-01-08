from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()


# ============================================
# Auth Service Endpoints
# ============================================


@router.api_route(
    "/auth/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_auth(request: Request, path: str):
    """
    Проксирует /auth/* запросы к Auth Service

    Примеры:
    - POST /api/auth/register → Auth Service
    - POST /api/auth/login → Auth Service
    - POST /api/auth/refresh → Auth Service
    - POST /api/auth/logout → Auth Service
    """
    user_data = None
    if hasattr(request.state, "user"):
        user_data = request.state.user

    return await proxy_request(
        request=request,
        target_url=settings.AUTH_SERVICE_URL,
        path=f"/api/auth/{path}",
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
        path=f"/api/users/{path}",
        user_data=user_data,
    )


# ============================================
# Main Service Endpoints
# ============================================


@router.api_route(
    "/tables/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_tables(request: Request, path: str):
    """
    Проксирует /tables/* запросы к Main Service
    """
    user_data = None
    if hasattr(request.state, "user"):
        user_data = request.state.user

    return await proxy_request(
        request=request,
        target_url=settings.MAIN_SERVICE_URL,
        path=f"/api/tables/{path}",
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
        path=f"/api/categories/{path}",
        user_data=user_data,
    )
