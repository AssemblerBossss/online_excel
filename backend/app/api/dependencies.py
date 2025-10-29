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
    Retrieves an instance of the table service.
    Args:
        table_repository: An instance of the table repository.
    Returns:
        TableService: An instance of the table service.
    """
    return TableService(table_repository=table_repository)


def get_user_service() -> UserService:
    """
    Retrieves an instance of the user service.
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
        data_repo: An instance of the data repository.
        table_repo: An instance of the table repository.
    Returns:
        DataService: An instance of the data service.
    """
    return DataService(data_repo, table_repo)
