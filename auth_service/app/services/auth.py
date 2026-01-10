import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from auth_service.app.config import auth_service_settings
from auth_service.app.exceptions import (
    UserAlreadyExistsException,
    IncorrectEmailOrPasswordException,
)
from auth_service.app.repository import UserRepository
from auth_service.app.schemas import (
    SUserRegister,
    SUserFilter,
    SUserAddDB,
    SUserInfo,
    SUserAuth,
    TokenData,
)
from auth_service.app.models import RefreshToken
from auth_service.app.utils import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    create_refresh_token,
)


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
        self, request: Request, user_data: SUserAuth
    ) -> Dict[str, Any]:
        user = await self.user_repo.find_one_or_none(
            filters=SUserFilter(email=user_data.email)
        )

        if not (
            user and await authenticate_user(user=user, password=user_data.password)
        ):
            raise IncorrectEmailOrPasswordException

        token_data = TokenData.model_validate(user)
        access_token = create_access_token(data=token_data.model)
        refresh_token = create_refresh_token()

        refresh_token_expires = datetime.utcnow() + datetime.timedelta(
            days=auth_service_settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        refresh_token_db = RefreshToken(
            token=refresh_token,
            user_id=user.id,
            expires_at=refresh_token_expires,
            user_agent=request.headers.get("User-Agent") if request else None,
            ip_address=request.client.host if request else None,
        )

        db.add(refresh_token_db)
        await db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_value,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def logout(self, response: Response) -> Dict[str, Any]:
        response.delete_cookie("user_access_token")
        response.delete_cookie("user_refresh_token")

    async def refresh_tokens(self, response: Response, user_id: int) -> Dict[str, Any]:
        set_tokens(response, user_id)
