from sqlalchemy.ext.asyncio import AsyncSession


class Base:
    """Базовый класс для репозиториев"""

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: SQLAlchemy AsyncSession из dependency
        """
        self._session = session
