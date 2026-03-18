from typing import Annotated
from fastapi import APIRouter, Response, Depends, Request
from fastapi import status

from auth_service.app.schemas import SUserRegister, SUserAuth, Token, TokenRefresh
from auth_service.app.services import AuthService
from auth_service.app.dependency import get_auth_service
from auth_service.app.сore import UnitOfWork, get_async_uow_session

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: SUserRegister,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth_service.register_user(user_data)
    return {"message": "Вы успешно зарегистрированы!"}


@router.post("/login", response_model=Token)
async def auth_user(
    request: Request,
    user_data: SUserAuth,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
):
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    tokens = await auth_service.login_user(
        user_data=user_data,
        user_agent=user_agent,
        ip_address=ip_address,
        uow_session=uow_session,
    )
    return tokens


@router.post("/logout")
async def logout(
    token_data: TokenRefresh,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    result = await auth_service.logout(refresh_token=token_data.refresh_token)
    return result


@router.post("/refresh", response_model=Token)
async def refresh_tokens(
    request: Request,
    token_data: TokenRefresh,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """Обновление токенов"""
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    tokens = await auth_service.refresh_tokens(
        refresh_token=token_data.refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return tokens
