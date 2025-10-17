from typing import List
from fastapi import APIRouter, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User
from .utils import authenticate_user, set_tokens
from backend.app.dependencies.auth_dep import get_current_user, get_current_admin_user, check_refresh_token
from backend.app.dependencies.dao_dep import get_session_with_commit, get_session_without_commit
from backend.app.exceptions import UserAlreadyExistsException, IncorrectEmailOrPasswordException
from backend.app.auth.dao import UsersDAO
from backend.app.auth.schemas import SUserRegister, SUserAuth, EmailModel, SUserAddDB, SUserInfo

router = APIRouter()


@router.post("/register/")
async def register_user(user_data: SUserRegister,
                        session: AsyncSession = Depends(get_session_with_commit)) -> dict:
    # Проверка существования пользователя
    user_dao = UsersDAO(session)

    existing_user = await user_dao.find_one_or_none(filters=EmailModel(email=user_data.email))
    if existing_user:
        raise UserAlreadyExistsException

    # Подготовка данных для добавления
    user_data_dict = user_data.model_dump()
    user_data_dict.pop('confirm_password', None)

    # Добавление пользователя
    await user_dao.add(values=SUserAddDB(**user_data_dict))

    return {'message': 'Вы успешно зарегистрированы!'}


@router.post("/login/")
async def auth_user(
        response: Response,
        user_data: SUserAuth,
        session: AsyncSession = Depends(get_session_without_commit)
) -> dict:
    users_dao = UsersDAO(session)
    user = await users_dao.find_one_or_none(
        filters=EmailModel(email=user_data.email)
    )

    if not (user and await authenticate_user(user=user, password=user_data.password)):
        raise IncorrectEmailOrPasswordException
    set_tokens(response, user.id)
    return {
        'ok': True,
        'message': 'Авторизация успешна!'
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("user_access_token")
    response.delete_cookie("user_refresh_token")
    return {'message': 'Пользователь успешно вышел из системы'}


@router.get("/me/")
async def get_me(user_data: User = Depends(get_current_user)) -> SUserInfo:
    return SUserInfo.model_validate(user_data)


@router.get("/all_users/")
async def get_all_users(session: AsyncSession = Depends(get_session_with_commit),
                        user_data: User = Depends(get_current_admin_user)
                        ) -> List[SUserInfo]:
    return await UsersDAO(session).find_all()


@router.post("/refresh")
async def process_refresh_token(
        response: Response,
        user: User = Depends(check_refresh_token)
):
    set_tokens(response, user.id)
    return {"message": "Токены успешно обновлены"}
