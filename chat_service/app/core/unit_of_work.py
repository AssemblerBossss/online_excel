from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from chat_service.app.repository import ChatRepository, ElasticSearchUserRepository


class UnitOfWork:
    """Unit of Work — управляет транзакциями и предоставляет доступ к репозиториям."""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        es_repo: ElasticSearchUserRepository,
    ):
        self.session_factory = session_factory
        self._session: AsyncSession | None = None
        self._es_repo = es_repo

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

    @property
    def es_users(self) -> ElasticSearchUserRepository:
        # Просто отдаёт уже готовый (переданный в конструктор) репозиторий —
        # не создаёт ничего нового, не требует активной сессии.
        return self._es_repo
