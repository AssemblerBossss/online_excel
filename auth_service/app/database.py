from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from auth_service.app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_maker = sessionmaker(
    engine=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Создание таблиц при старте"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
