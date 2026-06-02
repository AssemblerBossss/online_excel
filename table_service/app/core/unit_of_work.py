from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from table_service.app.repository import (
    TableRepository,
    DataRepository,
    PermissionRepository,
    UserRepository,
)


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
    def tables(self) -> TableRepository:
        return TableRepository(self._session)

    @property
    def data(self) -> DataRepository:
        return DataRepository(self._session)

    @property
    def permissions(self) -> PermissionRepository:
        return PermissionRepository(self._session)

    @property
    def users(self) -> UserRepository:
        return UserRepository(self._session)
