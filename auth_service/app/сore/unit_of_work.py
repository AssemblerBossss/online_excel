from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.app.repository import UserRepository
from auth_service.app.repository import TokenRepository


class UnitOfWork:
    """Unit of Work — управляет транзакциями и предоставляет доступ к репозиториям."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self._session: AsyncSession | None = None

    @asynccontextmanager
    async def start(self):
        self._session = self.session_factory()
        try:
            yield self
            await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            raise e
        finally:
            await self._session.close()

    @property
    def user(self) -> UserRepository:
        return UserRepository(self._session)

    @property
    def token(self) -> TokenRepository:
        return TokenRepository(self._session)
