from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timezone

from auth_service.app.models import RefreshToken
from loguru import logger


class TokenRepository:
    """Репозиторий для работы с refresh tokens"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_refresh_token(
        self,
        refresh_token: str,
        user_id: int,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[RefreshToken]:
        """
        Создать новый refresh token

        Args:
            refresh_token: Строка refresh токена
            user_id: ID пользователя
            expires_at: Время истечения токена
            user_agent: User agent клиента
            ip_address: IP адрес клиента

        Returns:
            Созданный RefreshToken
        """

        try:
            token_record = RefreshToken(
                refresh_token=refresh_token,
                user_id=user_id,
                expires_at=expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
                revoked=False
            )

            self._session.add(token_record)
            await self._session.flush()

            logger.info(
                "Создан refresh token для пользователя {} с ID {}".format(user_id, token_record.id)
            )
            return token_record

        except SQLAlchemyError as e:
            logger.error("Ошибка при создании refresh token: {}".format(e))


    async def find_by_token(self, refresh_token: str) ->Optional[RefreshToken]:
        try:
            query = select(RefreshToken).where(RefreshToken.refresh_token == refresh_token)
            result = await self._session.execute(query)
            token = result.scalar_one_or_none()

            if token:
                logger.debug("Refresh token найден: ID {}".format(token.id))
            else:
                logger.debug("Refresh token не найден")

            return token
        except SQLAlchemyError as e:
            logger.error("Ошибка при поиске refresh token: {}".format(e))
            raise

    async def validate_refresh_token(self, refresh_token: str) -> Optional[RefreshToken]:
        token = await self.find_by_token(refresh_token)

        if not token:
            logger.warning("Refresh token не найден в БД")
            return None
        if token.revoked:
            logger.warning("Refresh token {} был отозван".format(token.id))
            return None
        if token.expires_at < datetime.now(timezone.utc):
            logger.warning("Refresh token {} истек".format(token.id))
            return None

        logger.debug("Refresh token {} валиден".format(token.id))
        return token

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        try:
            token = await self.find_by_token(refresh_token)
            if not token:
                logger.warning("Токен для отзыва не найден")
                return False
            token.revoked = True
            await self._session.flush()

            logger.info("Refresh token {} отозван".format(token.id))
            return True
        except SQLAlchemyError as e:
            logger.error("Ошибка при отзыве токена: {}".format(e))
            raise