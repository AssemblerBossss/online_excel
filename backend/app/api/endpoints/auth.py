from typing import Annotated

from fastapi import APIRouter, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from backend.app.api.dependencies import get_user_service, get_auth_service
from backend.app.models import User
from backend.app.api.jwt_utils import set_tokens

from backend.app.api.jwt_utils import (
    get_current_user,
    get_admin_user,
    check_refresh_token,
)
from backend.app.dependencies.database_dependencies import (
    get_session_with_commit,
    get_session_without_commit,
)
from backend.app.exceptions import (
    UserAlreadyExistsException,
    IncorrectEmailOrPasswordException,
)
from backend.app.repository import UserRepository
from backend.app.schemas.user import (
    SUserRegister,
    SUserAuth,
    SUserInfo,
    SUserFilter,
    SUserAddDB,
)
from backend.app.services import UserService, AuthService
from backend.app.utils import authenticate_user

router = APIRouter()


@router.post("/register/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: SUserRegister, auth_service: Annotated[AuthService, get_auth_service]
):
    await auth_service.register_user(user_data)
    return {"message": "Вы успешно зарегистрированы!"}


@router.post("/login/")
async def auth_user(
    response: Response,
    user_data: SUserAuth,
    session: AsyncSession = Depends(get_session_without_commit),
) -> dict:
    users_dao = UserRepository(session)
    user = await users_dao.find_one_or_none(filters=SUserFilter(email=user_data.email))

    if not (user and await authenticate_user(user=user, password=user_data.password)):
        raise IncorrectEmailOrPasswordException
    set_tokens(response, user.id)
    return {"ok": True, "message": "Авторизация успешна!"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("user_access_token")
    response.delete_cookie("user_refresh_token")
    return {"message": "Пользователь успешно вышел из системы"}


@router.post("/refresh")
async def process_refresh_token(
    response: Response, user: User = Depends(check_refresh_token)
):
    set_tokens(response, user.id)
    return {"message": "Токены успешно обновлены"}
