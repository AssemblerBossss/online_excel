from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from table_service.app.core.database import AsyncSessionFactory


class Base:
    """Базовый класс для репозиториев"""

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: SQLAlchemy AsyncSession из dependency
        """
        self._session = session
