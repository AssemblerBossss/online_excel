from fastapi import Depends, Request, HTTPException
from typing import AsyncGenerator, Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from table_service.app.services import DataService, TableService
from table_service.app.repository import TableRepository, DataRepository, UserRepository
from table_service.app.core import AsyncSessionFactory
from table_service.app.schemas import SUserInfo, SUserFilter, SCurrentUser


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


def get_table_service(
    table_repository: TableRepository = Depends(get_table_repository),
    data_repository: DataRepository = Depends(get_data_repository),
) -> TableService:
    """
    Получить экземпляр сервиса таблиц.

    Args:
        table_repository: Экземпляр репозитория таблиц.
        data_repository: Экземпляр репозитория данных.

    Returns:
        TableService: Экземпляр сервиса таблиц.
    """
    return TableService(
        table_repository=table_repository, data_repository=data_repository
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


async def get_current_user(request: Request) -> SUserFilter:
    """Извлекает данные пользователя из request.state (заполняется JWT middleware)."""
    payload = getattr(request.state, "user", None)
    if payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return SUserFilter(**payload)


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
