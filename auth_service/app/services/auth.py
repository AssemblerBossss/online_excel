import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from auth_service.app.config import auth_service_settings
from auth_service.app.exceptions import (
    UserAlreadyExistsException,
    IncorrectEmailOrPasswordException,
    InvalidRefreshTokenException,
    UserInactiveException,
)
from auth_service.app.schemas import UserRegisterEvent
from auth_service.app.сore.unit_of_work import UnitOfWork
from auth_service.app.events import event_publisher
from auth_service.app.models import User, RefreshToken
from auth_service.app.schemas import (
    SUserRegister,
    SUserAuth,
    Token,
)
from auth_service.app.utils import (
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self):
        self.event_publisher = event_publisher

    def _build_token_data(self, user: User) -> dict:
        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
        }

    def _create_refresh_token_data(self) -> tuple[str, datetime]:
        """Создать пару (refresh_token, expires_at)."""
        refresh_token = create_refresh_token()
        expires = datetime.now(timezone.utc) + timedelta(
            days=auth_service_settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        return refresh_token, expires

    def _build_token_response(self, access_token: str, refresh_token: str) -> Token:
        """Создать ответ с токенами."""
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=auth_service_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def register_user(
        self, user_data: SUserRegister, uow_session: UnitOfWork
    ) -> User:
        """Регистрирует нового пользователя."""
        async with uow_session.start():
            if await uow_session.user.find_by_email(email=user_data.email):
                raise UserAlreadyExistsException

            hashed_password = get_password_hash(user_data.password)

            user = User(
                email=user_data.email,
                hashed_password=hashed_password,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
            )
            await uow_session.user.add(user)

        event = UserRegisterEvent(
            user_id=user.id,
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
        uow_session: UnitOfWork,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Token:
        """Аутентифицирует пользователя и возвращает токены."""
        async with uow_session.start():
            user = await uow_session.user.find_by_email(email=user_data.email)

            if not user or not verify_password(
                user_data.password, user.hashed_password
            ):
                raise IncorrectEmailOrPasswordException

            access_token = create_access_token(data=self._build_token_data(user))
            refresh_token, refresh_token_expires = self._create_refresh_token_data()

            token = RefreshToken(
                refresh_token=refresh_token,
                user_id=user.id,
                expires_at=refresh_token_expires,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            await uow_session.token.add(token=token)

            logger.info("Refresh token создан для %s", user.email)

            logger.info("Пользователь %s успешно вошел в систему", user.email)
            return self._build_token_response(access_token, refresh_token)

    async def refresh_tokens(
        self,
        refresh_token: str,
        uow_session: UnitOfWork,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Token:
        """хранит локальную таблицу пользователей
        Обновление токенов по refresh token

        Args:
            refresh_token: Refresh token
            user_agent: User agent клиента
            ip_address: IP адрес клиента
            uow_session:

        Returns:
            Token: Новые access token и refresh token

        Raises:
            HTTPException: Если refresh token невалиден
        """
        async with uow_session.start():
            token_record: RefreshToken = await uow_session.token.find_by_token(
                refresh_token=refresh_token
            )
            if (
                not token_record
                or token_record.revoked
                or token_record.expires_at < datetime.now(timezone.utc)
            ):
                raise InvalidRefreshTokenException()

            user = await uow_session.user.find_one_or_none_by_id(
                user_id=token_record.user_id
            )
            if not user or not user.is_active:
                raise UserInactiveException()

            new_access_token = create_access_token(data=self._build_token_data(user))
            new_refresh_token, refresh_token_expires = self._create_refresh_token_data()

            await uow_session.token.update(
                filters={"refresh_token": refresh_token}, values={"revoked": True}
            )

            token = RefreshToken(
                refresh_token=new_refresh_token,
                user_id=user.id,
                expires_at=refresh_token_expires,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            await uow_session.token.add(token=token)
            logger.info("Refresh token обновлен для %s", user.email)

        return self._build_token_response(new_access_token, new_refresh_token)

    async def logout(
        self, refresh_token: str, uow_session: UnitOfWork
    ) -> Dict[str, str]:
        async with uow_session.start():
            await uow_session.token.update(
                filters={"refresh_token": refresh_token}, values={"revoked": True}
            )
            logger.info("Пользователь вышел из системы")

        return {"message": "Успешный выход из системы"}

    async def logout_all_devices(
        self, user_id: int, uow_session: UnitOfWork
    ) -> Dict[str, str]:

        async with uow_session.start():
            count = await uow_session.token.revoke_all_user_tokens(user_id=user_id)

            logger.info("Пользователь %s вышел со всех устройств (%s)", user_id, count)

        return {"message": f"Выход выполнен на {count} устройствах"}
