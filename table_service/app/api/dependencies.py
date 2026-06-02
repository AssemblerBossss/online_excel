from elasticsearch import AsyncElasticsearch
from fastapi import Depends, Request, HTTPException
from typing import AsyncGenerator, Annotated
from redis.asyncio import Redis

from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.services import (
    DataService,
    TableService,
    SearchService,
    PermissionService,
    ExcelProcessorService,
)
from table_service.app.core import AsyncSessionFactory, get_redis_client, get_es_client
from table_service.app.schemas import SCurrentUser, SUserFilter
from table_service.app.services.data_validation import DataValidationService


async def get_async_uow_session() -> AsyncGenerator[UnitOfWork, None]:
    yield UnitOfWork(AsyncSessionFactory)


def get_search_service(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
) -> SearchService:
    """Получить экземпляр сервиса поиска (Elasticsearch)."""
    return SearchService(es_client=es)


async def get_validation_service() -> DataValidationService:
    """Получить экземпляр сервиса валидации данных."""
    return DataValidationService()


def get_permission_service() -> PermissionService:
    """Получить экземпляр сервиса разрешений пользователей."""
    return PermissionService()


def get_excel_processor_service() -> ExcelProcessorService:
    """Получить экземпляр сервиса обработки Excel."""
    return ExcelProcessorService()


def get_table_service(
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
    excel_processor: Annotated[
        ExcelProcessorService, Depends(get_excel_processor_service)
    ],
) -> TableService:
    """Получить экземпляр сервиса таблиц."""
    return TableService(
        permission_service=permission_service,
        search_service=search_service,
        excel_processor=excel_processor,
    )


def get_data_service(
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    validation_service: Annotated[
        DataValidationService, Depends(get_validation_service)
    ],
) -> DataService:
    """Получить экземпляр сервиса данных."""
    return DataService(
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
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SCurrentUser:
    """Проверяет актуальность пользователя в БД (UserProjection синхронизируется через RabbitMQ)."""
    async with uow_session.start():
        user = await uow_session.users.get_by_id(payload.user_id)
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
