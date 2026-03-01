from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork:
    """Асинхронный Unit of Work для управления транзакциями БД.

    Оборачивает сессию SQLAlchemy, автоматически коммитит при успехе
    или откатывает при исключении.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            await self.session.rollback()
        else:
            await self.session.commit()
