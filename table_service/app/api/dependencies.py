from elasticsearch import AsyncElasticsearch
from fastapi import Depends, Request, HTTPException
from typing import AsyncGenerator, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from table_service.app.services import DataService, TableService, SearchService
from table_service.app.repository import TableRepository, DataRepository, UserRepository
from table_service.app.core import AsyncSessionFactory, get_redis_client, get_es_client
from table_service.app.schemas import SCurrentUser, SUserFilter


async def get_session_with_commit() -> AsyncGenerator[AsyncSession, None]:
    """
    Получить асинхронную сессию с автоматическим коммитом.

    Returns:
        AsyncGenerator[AsyncSession, None]: Асинхронная сессия с автокоммитом.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session_without_commit() -> AsyncGenerator[AsyncSession, None]:
    """
    Получить асинхронную сессию без автоматического коммита.

    Returns:
        AsyncGenerator[AsyncSession, None]: Асинхронная сессия без автокоммита.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_table_repository(
    session: AsyncSession = Depends(get_session_with_commit),
) -> TableRepository:
    """
    Получить экземпляр репозитория таблиц.

    Args:
        session: Асинхронная сессия с автоматическим коммитом.

    Returns:
        TableRepository: Экземпляр репозитория таблиц.
    """
    return TableRepository(session=session)


def get_data_repository(
    session: AsyncSession = Depends(get_session_with_commit),
) -> DataRepository:
    """
    Получить экземпляр репозитория данных.

    Args:
        session: Асинхронная сессия с автоматическим коммитом.

    Returns:
        DataRepository: Экземпляр репозитория данных.
    """
    return DataRepository(session=session)


def get_user_repository(
    session: AsyncSession = Depends(get_session_without_commit),
) -> UserRepository:
    """
    Получить экземпляр репозитория пользователей.

    Args:
        session: Асинхронная сессия без автоматического коммита.

    Returns:
        UserRepository: Экземпляр репозитория пользователей.
    """
    return UserRepository(session=session)


def get_search_service(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
) -> SearchService:
    return SearchService(es_client=es)


def get_table_service(
    table_repository: Annotated[TableRepository, Depends(get_table_repository)],
    data_repository: Annotated[DataRepository, Depends(get_data_repository)],
    es: Annotated[SearchService, Depends(get_search_service)],
) -> TableService:
    """
    Получить экземпляр сервиса таблиц.

    Args:
        table_repository: Экземпляр репозитория таблиц.
        data_repository: Экземпляр репозитория данных.
        es: Сервис Elasticsearch.

    Returns:
        TableService: Экземпляр сервиса таблиц.

    """
    return TableService(
        table_repository=table_repository,
        data_repository=data_repository,
        search_service=es,
    )


def get_data_service(
    data_repo: DataRepository = Depends(get_data_repository),
    table_repo: TableRepository = Depends(get_table_repository),
) -> DataService:
    """
    Получить экземпляр сервиса данных.

    Args:
        data_repo: Экземпляр репозитория данных.
        table_repo: Экземпляр репозитория таблиц.

    Returns:
        DataService: Экземпляр сервиса данных.
    """
    return DataService(data_repo, table_repo)


def get_redis() -> Redis:
    return get_redis_client()


async def get_current_user(request: Request) -> SUserFilter:
    """Извлекает данные пользователя из request.state (заполняется JWT middleware)."""
    user_id = request.headers.get("X-User-ID")
    email = request.headers.get("X-User-Email")
    role = request.headers.get("X-User-Role")
    is_active = request.headers.get("X-User-Active")
    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return SUserFilter(
        user_id=int(user_id),
        email=email,
        role=role,
        is_active=is_active.lower() == "true" if is_active else False,
    )


async def get_current_active_user(
    payload: Annotated[SUserFilter, Depends(get_current_user)],
    user_repo: UserRepository = Depends(get_user_repository),
) -> SCurrentUser:
    """Проверяет актуальность пользователя в БД (UserProjection синхронизируется через RabbitMQ)."""
    user = await user_repo.get_by_id(payload.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return SCurrentUser(
        user_id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
