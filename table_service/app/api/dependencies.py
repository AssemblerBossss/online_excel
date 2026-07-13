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
    WsTicketService,
    RowEventPublisher,
    DataValidationService,
    ExportJobService,
)
from table_service.app.core import (
    AsyncSessionFactory,
    get_redis_client,
    get_es_client,
    export_storage,
    ExportStorage,
)
from table_service.app.schemas import SCurrentUser, SUserFilter


async def get_async_uow_session() -> AsyncGenerator[UnitOfWork, None]:
    yield UnitOfWork(AsyncSessionFactory)


def get_redis() -> Redis:
    """Получить асинхронный клиент Redis."""
    return get_redis_client()


def get_export_storage() -> ExportStorage:
    """Получить хранилище файлов экспорта (MinIO)."""
    return export_storage


def get_row_event_publisher(
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> RowEventPublisher:
    """Получить издателя событий строк (Redis Pub/Sub)."""
    return RowEventPublisher(redis=redis)


def get_ws_ticket_service(
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> WsTicketService:
    """Получить сервис одноразовых WebSocket-тикетов."""
    return WsTicketService(redis=redis)


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
    event_publisher: Annotated[RowEventPublisher, Depends(get_row_event_publisher)],
) -> DataService:
    """Получить экземпляр сервиса данных."""
    return DataService(
        permission_service=permission_service,
        validation_service=validation_service,
        event_publisher=event_publisher,
    )


def get_export_job_service(
    redis: Annotated[Redis, Depends(get_redis)],
    storage: Annotated[ExportStorage, Depends(get_export_storage)],
    excel_processor: Annotated[
        ExcelProcessorService, Depends(get_excel_processor_service)
    ],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> ExportJobService:
    """Получить сервис фонового экспорта таблиц."""
    return ExportJobService(
        redis=redis,
        storage=storage,
        excel_processor=excel_processor,
        permission_service=permission_service,
    )


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
