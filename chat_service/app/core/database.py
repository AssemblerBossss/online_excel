from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
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


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
