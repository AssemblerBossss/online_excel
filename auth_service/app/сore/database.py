from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from auth_service.app.config import auth_service_settings
from auth_service.app.models import Base
from .unit_of_work import UnitOfWork

engine = create_async_engine(auth_service_settings.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Создание таблиц при старте"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_uow_session() -> AsyncGenerator[UnitOfWork, None]:
    yield UnitOfWork(async_session_maker)
