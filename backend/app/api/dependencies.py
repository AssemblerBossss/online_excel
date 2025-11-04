from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from backend.app.services import DataService, TableService, UserService, AuthService
from backend.app.repository import TableRepository, DataRepository, UserRepository
from backend.app.dependencies import get_session_with_commit, get_session_without_commit


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


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_session_with_commit)],
) -> UserService:
    """
    Retrieves an instance of the user service.
    Args:
        session: An instance of the database session.
    Returns:
        UserService: An instance of the user service.
    """
    return UserService(session=session)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session_with_commit)],
):
    """
    Retrieves an instance of the auth service.
    Args:
        session: An instance of the database session.
    Returns:
        AuthService: An instance of the auth service.
    """
    return AuthService(session=session)


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
