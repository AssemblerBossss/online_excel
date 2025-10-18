from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionFactory


class Base:

    def __init__(self):
        self.session_factory = AsyncSessionFactory

    @asynccontextmanager
    async def _session_scope(self) -> AsyncSession:
        """Context manager for handling database sessions.

        Provides automatic transaction management with commit/rollback
        and proper session cleanup.
        """
        async with self.session_factory() as session:
            try:
                session.expire_on_commit = False
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
