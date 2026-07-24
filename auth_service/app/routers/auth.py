from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from starlette.responses import JSONResponse

from auth_service.app.dependency import get_auth_service
from auth_service.app.schemas import SUserAuth, SUserRegister, Token, TokenRefresh
from auth_service.app.services import AuthService
from auth_service.app.сore import UnitOfWork, get_async_uow_session, limiter

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register_user(
    request: Request,
    user_data: SUserRegister,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
):
    await auth_service.register_user(
        user_data,
        uow_session=uow_session,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Вы успешно зарегистрированы!"},
    )


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
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
    return JSONResponse(status_code=status.HTTP_200_OK, content=tokens.model_dump())


@router.post("/logout")
@limiter.limit("20/minute")
async def logout(
    request: Request,
    token_data: TokenRefresh,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
):
    result = await auth_service.logout(
        refresh_token=token_data.refresh_token, uow_session=uow_session
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh_tokens(
    request: Request,
    token_data: TokenRefresh,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
):
    """Обновление токенов"""
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    tokens = await auth_service.refresh_tokens(
        refresh_token=token_data.refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
        uow_session=uow_session,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=tokens.model_dump())
