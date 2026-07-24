from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from auth_service.app.config import auth_service_settings

from .unit_of_work import UnitOfWork

engine = create_async_engine(auth_service_settings.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with async_session_maker() as session:
        yield session


async def get_async_uow_session() -> AsyncGenerator[UnitOfWork]:
    yield UnitOfWork(async_session_maker)
