from typing import Annotated
from fastapi import APIRouter, Response, Depends
from fastapi import status

from backend.app.api.dependencies import get_auth_service
from backend.app.models import User
from backend.app.api.jwt_utils import check_refresh_token
from backend.app.schemas.user import SUserRegister, SUserAuth
from backend.app.services import AuthService

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
