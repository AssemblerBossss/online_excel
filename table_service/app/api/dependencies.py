from elasticsearch import AsyncElasticsearch
from fastapi import Depends, Request, HTTPException
from typing import AsyncGenerator, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from table_service.app.services import (
    DataService,
    TableService,
    SearchService,
    PermissionService,
    ExcelProcessorService,
)
from table_service.app.repository import (
    TableRepository,
    DataRepository,
    UserRepository,
    PermissionRepository,
)
from table_service.app.core import AsyncSessionFactory, get_redis_client, get_es_client
from table_service.app.schemas import SCurrentUser, SUserFilter
from table_service.app.services.data_validation import DataValidationService


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


def get_table_repository(
    session: Annotated[AsyncSession, Depends(get_session_with_commit)],
) -> TableRepository:
    """Получить экземпляр репозитория таблиц."""
    return TableRepository(session=session)


def get_data_repository(
    session: Annotated[AsyncSession, Depends(get_session_with_commit)],
) -> DataRepository:
    """Получить экземпляр репозитория данных."""
    return DataRepository(session=session)


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session_with_commit)],
) -> UserRepository:
    """Получить экземпляр репозитория пользователей."""
    return UserRepository(session=session)


def get_permission_repository(
    session: Annotated[AsyncSession, Depends(get_session_with_commit)],
) -> PermissionRepository:
    """Получить экземпляр репозитория разрешения пользователей."""
    return PermissionRepository(session=session)


def get_search_service(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
) -> SearchService:
    """Получить экземпляр сервиса поиска (Elasticsearch)."""
    return SearchService(es_client=es)


async def get_validation_service() -> DataValidationService:
    """Получить экземпляр сервиса валидации данных."""
    return DataValidationService()


def get_permission_service(
    table_repo: Annotated[TableRepository, Depends(get_table_repository)],
    permission_repo: Annotated[
        PermissionRepository, Depends(get_permission_repository)
    ],
) -> PermissionService:
    """Получить экземпляр сервиса разрешений пользователей."""
    return PermissionService(table_repo=table_repo, permission_repo=permission_repo)


def get_excel_processor_service() -> ExcelProcessorService:
    """Получить экземпляр сервиса обработки Excel."""
    return ExcelProcessorService()


def get_table_service(
    table_repo: Annotated[TableRepository, Depends(get_table_repository)],
    data_repo: Annotated[DataRepository, Depends(get_data_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
    excel_processor: Annotated[
        ExcelProcessorService, Depends(get_excel_processor_service)
    ],
) -> TableService:
    """Получить экземпляр сервиса таблиц."""
    return TableService(
        table_repository=table_repo,
        data_repository=data_repo,
        permission_service=permission_service,
        search_service=search_service,
        excel_processor=excel_processor,
    )


def get_data_service(
    data_repo: Annotated[DataRepository, Depends(get_data_repository)],
    table_repo: Annotated[TableRepository, Depends(get_table_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    validation_service: Annotated[
        DataValidationService, Depends(get_validation_service)
    ],
) -> DataService:
    """Получить экземпляр сервиса данных."""
    return DataService(
        data_repo=data_repo,
        table_repo=table_repo,
        permission_service=permission_service,
        validation_service=validation_service,
    )


def get_redis() -> Redis:
    """Получить асинхронный клиент Redis."""
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
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
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
