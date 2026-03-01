import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, UTC, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from auth_service.app.config import auth_service_settings
from auth_service.app.exceptions import (
    UserAlreadyExistsException,
    IncorrectEmailOrPasswordException,
)
from auth_service.app.schemas import UserRegisterEvent
from auth_service.app.unit_of_work import UnitOfWork
from auth_service.app.events import event_publisher
from auth_service.app.models import User
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

logger = logging.getLogger(__name__)


class AuthService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = TokenRepository(session)
        self.event_publisher = event_publisher

    async def register_user(self, user_data: SUserRegister) -> User:
        """Регистрирует нового пользователя."""
        async with UnitOfWork(self.session):

            if await self.user_repo.find_by_email(email=user_data.email):
                raise UserAlreadyExistsException

            hashed_password = get_password_hash(user_data.password)

            user = User(
                email=user_data.email,
                hashed_password=hashed_password,
                role=user_data.role,
            )

            await self.user_repo.add(user)

        event = UserRegisterEvent(
            user_id=str(user.id),
            email=user.email,
            role=str(user.role),
            timestamp=datetime.now(timezone.utc),
        )
        await self.event_publisher.publish(event)
        logger.info("Событие user.registered опубликовано для {}".format(user.email))

        return user

    async def login_user(
        self,
        user_data: SUserAuth,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Token:
        """Аутентифицирует пользователя и возвращает токены."""
        user = await self.user_repo.find_by_email(email=user_data.email)

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

        async with UnitOfWork(self.session):
            await self.token_repo.create_refresh_token(
                refresh_token=refresh_token,
                user_id=user.id,
                expires_at=refresh_token_expires,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            logger.info("Refresh token создан для {}".format(user.email))

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
        """хранит локальную таблицу пользователей
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

        new_access_token = create_access_token(
            data={
                "user_id": user.id,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active,
            }
        )

        # Создаем новый refresh token
        new_refresh_token = create_refresh_token()
        refresh_token_expires = datetime.now(timezone.utc) + timedelta(
            days=auth_service_settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        async with UnitOfWork(self.session):

            await self.token_repo.revoke_refresh_token(refresh_token=refresh_token)

            await self.token_repo.create_refresh_token(
                refresh_token=new_refresh_token,
                user_id=user.id,
                expires_at=refresh_token_expires,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            logger.info(f"Refresh token обновлен для {user.email}")

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
            expires_in=auth_service_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str) -> Dict[str, str]:

        async with UnitOfWork(self.session):
            await self.token_repo.revoke_refresh_token(refresh_token=refresh_token)

            logger.info("Пользователь вышел из системы")

        return {"message": "Успешный выход из системы"}

    async def logout_all_devices(self, user_id: int) -> Dict[str, str]:

        async with UnitOfWork(self.session):
            count = await self.token_repo.revoke_all_user_tokens(user_id=user_id)

            logger.info(
                "Пользователь {} вышел со всех устройств ({})".format(user_id, count)
            )

        return {"message": f"Выход выполнен на {count} устройствах"}
