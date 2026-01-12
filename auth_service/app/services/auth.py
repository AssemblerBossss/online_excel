from contextlib import asynccontextmanager
from datetime import datetime, timedelta, UTC, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from auth_service.app.config import auth_service_settings
from auth_service.app.exceptions import (
    UserAlreadyExistsException,
    IncorrectEmailOrPasswordException,
)
from auth_service.app.repository import UserRepository, TokenRepository
from auth_service.app.schemas import (
    SUserRegister,
    SUserFilter,
    SUserAddDB,
    SUserAuth,
    Token,
)
from auth_service.app.models import RefreshToken
from auth_service.app.utils import (
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_password,
)


@asynccontextmanager
async def transaction(session: AsyncSession):
    """Контекстный менеджер для транзакций"""
    try:
        yield
        await session.commit()
    except Exception:
        await session.rollback()
        raise


class AuthService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = TokenRepository(session)

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
        async with transaction(self.session):
            new_user = await self.user_repo.add(user_data=SUserAddDB(**user_data_dict))
            return new_user
        # return await self.user_repo.add(user_data=SUserAddDB(**user_data_dict))

    async def login_user(
        self,
        user_data: SUserAuth,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Token:
        user = await self.user_repo.find_one_or_none(
            filters=SUserFilter(email=user_data.email)
        )

        if not user or not verify_password(user_data.password, user.hashed_password):
            raise IncorrectEmailOrPasswordException

        token_data = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token()

        refresh_token_expires = datetime.now(UTC) + timedelta(
            days=auth_service_settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.token_repo.create_refresh_token(
            refresh_token=refresh_token,
            user_id=user.id,
            expires_at=refresh_token_expires,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.session.commit()

        logger.info("Пользователь {} успешно вошел в систему".format(user.email))

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=auth_service_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_tokens(
        self,
        refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Token:
        """
        Обновление токенов по refresh token

        Args:
            refresh_token: Refresh token
            user_agent: User agent клиента
            ip_address: IP адрес клиента

        Returns:
            Token: Новые access token и refresh token

        Raises:
            HTTPException: Если refresh token невалиден
        """
        from fastapi import HTTPException

        # Валидируем refresh token
        token_record: RefreshToken = await self.token_repo.validate_refresh_token(
            refresh_token
        )
        if not token_record:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user = await self.user_repo.find_one_or_none_by_id(user_id=token_record.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        # Отзываем старый refresh token
        await self.token_repo.revoke_refresh_token(refresh_token=refresh_token)

        # Создаем новый access token
        token_data = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
        }
        new_access_token = create_access_token(data=token_data)

        # Создаем новый refresh token
        new_refresh_token = create_refresh_token()
        refresh_token_expires = datetime.now(timezone.utc) + timedelta(
            days=auth_service_settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.token_repo.create_refresh_token(
            refresh_token=new_refresh_token,
            user_id=user.id,
            expires_at=refresh_token_expires,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.session.commit()

        logger.info(f"Токены обновлены для пользователя {user.email}")

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
            expires_in=auth_service_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str) -> Dict[str, str]:
        await self.token_repo.revoke_refresh_token(refresh_token=refresh_token)
        await self.session.commit()
        return {"message": "Успешный выход из системы"}

    async def logout_all_devices(self, user_id: int) -> Dict[str, str]:
        count = self.token_repo.revoke_all_user_tokens(user_id=user_id)
        await self.session.commit()
        return {"message": f"Выход выполнен на {count} устройствах"}
