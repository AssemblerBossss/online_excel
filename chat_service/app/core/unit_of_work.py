from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from chat_service.app.repository import ChatRepository


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
        except Exception as e:
            await self._session.rollback()
            raise e
        finally:
            await self._session.close()
            self._session = None

    @property
    def chat_repo(self) -> ChatRepository:
        return ChatRepository(self._session)
