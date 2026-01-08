from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from backend.app.api import set_tokens
from backend.app.exceptions import (
    UserAlreadyExistsException,
    IncorrectEmailOrPasswordException,
)
from backend.app.repository import UserRepository
from backend.app.schemas import (
    SUserRegister,
    SUserFilter,
    SUserAddDB,
    SUserInfo,
    SUserAuth,
)
from backend.app.utils import get_password_hash, authenticate_user


class AuthService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register_user(self, user_data: SUserRegister) -> Dict[str, Any]:
        existing_user = await self.user_repo.find_one_or_none(
            filters=SUserFilter(email=user_data.email)
        )
        if existing_user:
            raise UserAlreadyExistsException

        hashed_password = get_password_hash(user_data.password)

        # Подготовка данных для добавления
        user_data_dict = user_data.model_dump()
        user_data_dict.pop("confirm_password", None)
        user_data_dict.pop("password", None)
        user_data_dict["hashed_password"] = hashed_password  # Заменяем на хеш

        await self.user_repo.add(user_data=SUserAddDB(**user_data_dict))

    async def login_user(
        self, response: Response, user_data: SUserAuth
    ) -> Dict[str, Any]:
        user = await self.user_repo.find_one_or_none(
            filters=SUserFilter(email=user_data.email)
        )

        if not (
            user and await authenticate_user(user=user, password=user_data.password)
        ):
            raise IncorrectEmailOrPasswordException

        set_tokens(response, user.id)

    async def logout(self, response: Response) -> Dict[str, Any]:
        response.delete_cookie("user_access_token")
        response.delete_cookie("user_refresh_token")

    async def refresh_tokens(self, response: Response, user_id: int) -> Dict[str, Any]:
        set_tokens(response, user_id)
