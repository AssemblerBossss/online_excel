from typing import Annotated
from fastapi import APIRouter, Response, Depends
from fastapi import status

from auth_service.app.models import User
from auth_service.app.schemas.user import SUserRegister, SUserAuth, Token, TokenRefresh

from auth_service.app.services import AuthService
from auth_service.app.dependency import get_auth_service

router = APIRouter()


@router.post("/register/", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: SUserRegister,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth_service.register_user(user_data)
    return {"message": "Вы успешно зарегистрированы!"}


@router.post("/login/")
async def auth_user(
    response: Response,
    user_data: SUserAuth,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth_service.login_user(response=response, user_data=user_data)
    return {"ok": True, "message": "Авторизация успешна!"}


@router.post("/logout")
async def logout(
    response: Response, auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    await auth_service.logout(response=response)
    return {"message": "Пользователь успешно вышел из системы"}


@router.post("/refresh")
async def process_refresh_token(
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user: User = Depends(check_refresh_token),
):
    await auth_service.refresh_tokens(response=response, user_id=user.id)
    return {"message": "Токены успешно обновлены"}
