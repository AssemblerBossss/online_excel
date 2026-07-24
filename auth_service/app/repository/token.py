import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.app.models import RefreshToken

logger = logging.getLogger(__name__)


class TokenRepository:
    """Репозиторий для работы с refresh tokens"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, token: RefreshToken) -> RefreshToken:
        """Создать новый refresh token"""
        self._session.add(token)
        await self._session.flush()
        return token

    async def update(self, filters: dict, values: dict) -> int:
        if not values:
            return 0
        query = (
            update(RefreshToken)
            .filter_by(**filters)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(query)
        await self._session.flush()
        return result.rowcount

    async def find_by_token(self, refresh_token: str) -> RefreshToken | None:
        """Найти refresh token по значению"""
        query = select(RefreshToken).where(RefreshToken.refresh_token == refresh_token)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def find_all_by_user_id(self, user_id: int) -> Sequence[RefreshToken] | None:
        """Найти refresh token пользователя"""
        query = select(RefreshToken).filter_by(user_id=user_id)
        result = (await self._session.execute(query)).scalars().all()
        return result

    async def find_not_revoked_by_user_id(self, user_id: int) -> Sequence[RefreshToken]:
        """Найти активные (не отозванные) refresh токены пользователя"""
        query = select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """Отозвать все refresh токены пользователя"""
        tokens = await self.find_not_revoked_by_user_id(user_id=user_id)
        count = 0
        for token in tokens:
            count += 1
            token.revoked = True

        await self._session.flush()
        return count

    async def delete_expired(self) -> int:
        query = delete(RefreshToken).where(
            RefreshToken.expires_at < datetime.now(UTC)
        )
        result = await self._session.execute(query)
        await self._session.flush()
        return int(result.rowcount)

    async def delete_token(self, refresh_token: str) -> bool:
        """Удалить refresh token из БД"""
        query = delete(RefreshToken).filter_by(refresh_token=refresh_token)
        result = await self._session.execute(query)
        await self._session.flush()

        deleted = int(result.rowcount)
        return deleted > 0

    async def count_active_user_tokens(self, user_id) -> int:
        """Подсчитать количество активных токенов пользователя"""
        tokens = await self.find_not_revoked_by_user_id(user_id=user_id)
        return len(tokens)
