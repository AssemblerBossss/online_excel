from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from table_service.app.repository import (
    DataRepository,
    PermissionRepository,
    TablePinRepository,
    TableRepository,
    UserRepository,
)


class UnitOfWork:
    """Unit of Work — управляет транзакциями и предоставляет доступ к репозиториям."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self._session: AsyncSession | None = None

    @asynccontextmanager
    async def start(self):
        # Вложенный вызов: сессия уже открыта — переиспользуем её,
        # не создаём новую и не коммитим/не закрываем раньше времени.
        # Границей транзакции владеет самый внешний start().
        if self._session is not None:
            yield self
            return

        self._session = self.session_factory()
        try:
            yield self
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        finally:
            await self._session.close()
            self._session = None

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

    @property
    def table_pins(self) -> TablePinRepository:
        return TablePinRepository(self._session)
