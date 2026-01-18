from fastapi import Depends
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from table_service.app.services import DataService, TableService
from table_service.app.repository import TableRepository, DataRepository
from table_service.app.core import AsyncSessionFactory


async def get_session_with_commit() -> AsyncGenerator[AsyncSession, None]:
    """Асинхронная сессия с автоматическим коммитом."""
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
    """Асинхронная сессия без автоматического коммита."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_table_repository() -> TableRepository:
    """
    Retrieves an instance of the table repository.
    Returns:
        TableRepository: An instance of the table repository.
    """
    return TableRepository()


def get_data_repository() -> DataRepository:
    """
    Retrieves an instance of the data repository.
    Returns:
        DataRepository: An instance of the data repository.
    """
    return DataRepository()


def get_table_service(
    table_repository: TableRepository = Depends(get_table_repository),
    data_repository: DataRepository = Depends(get_data_repository),
) -> TableService:
    """
    Retrieves an instance of the table service.
    Args:
        table_repository: An instance of the table repository.
        data_repository: An instance of the data repository.
    Returns:
        TableService: An instance of the table service.
    """
    return TableService(
        table_repository=table_repository, data_repository=data_repository
    )


def get_data_service(
    data_repo: DataRepository = Depends(get_data_repository),
    table_repo: TableRepository = Depends(get_table_repository),
) -> DataService:
    """
    Retrieves an instance of the data service.
    Args:
        data_repo: An instance of the data repository.
        table_repo: An instance of the table repository.
    Returns:
        DataService: An instance of the data service.
    """
    return DataService(data_repo, table_repo)
