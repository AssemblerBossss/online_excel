from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from .settings import app_settings

async_engine = create_async_engine(
    url=app_settings.db_url,
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


async def init_db():
    """Создание таблиц при старте"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""

    pass
