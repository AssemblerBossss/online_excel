from typing import AsyncGenerator
from fastapi import Depends

from backend.app.services import DataService, TableService, UserService
from backend.app.repository import TableRepository, DataRepository, UserRepository


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
) -> TableService:
    """
    Retrieves an instance of the task service.
    Args:
    Returns:
        TaskService: An instance of the task service.
    """
    return TableService(table_repository=table_repository)


def get_user_service() -> UserService:
    """
    Retrieves an instance of the user service.
    Args:
    Returns:
        UserService: An instance of the user service.
    """
    return UserService()


def get_data_service(
    data_repo: DataRepository = Depends(get_data_repository),
    table_repo: TableRepository = Depends(get_table_repository),
) -> DataService:
    """
    Retrieves an instance of the data service.
    Args:
    Returns:
        DataService: An instance of the data service.
    """
    return DataService(data_repo, table_repo)
