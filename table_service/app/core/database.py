from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .settings import app_settings

async_engine = create_async_engine(
    url=app_settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    autocommit=False,
)


async def get_db_session() -> AsyncSession:
    async with AsyncSessionFactory() as async_session:
        yield async_session


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""

