import json
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from redis.asyncio import Redis

from table_service.app.api.cache import (
    TABLES_CACHE_TTL,
    invalidate_tables_cache,
    invalidate_trash_cache,
    tables_cache_key,
)
from table_service.app.api.dependencies import (
    get_async_uow_session,
    get_current_active_user,
    get_export_job_service,
    get_redis,
    get_table_service,
    get_ws_ticket_service,
)
from table_service.app.core import AsyncSessionFactory
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.schemas import (
    DataTableCreate,
    DataTableDuplicate,
    DataTableResponse,
    DataTableUpdate,
    SCurrentUser,
    SExportJobCreated,
    SExportJobStatusResponse,
    SWsTicketResponse,
)
from table_service.app.services import ExportJobService, TableService, WsTicketService

router = APIRouter()


@router.get("/export-jobs/{job_id}", response_model=SExportJobStatusResponse)
async def get_export_job_status(
    job_id: str,
    export_service: Annotated[ExportJobService, Depends(get_export_job_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
) -> SExportJobStatusResponse:
    """Статус задачи экспорта; при готовности — presigned-ссылка на скачивание."""
    return await export_service.get_status(job_id, current_user)


@router.post(
    "/{table_id}/export-jobs",
    response_model=SExportJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_table_export(
    table_id: int,
    background_tasks: BackgroundTasks,
    export_service: Annotated[ExportJobService, Depends(get_export_job_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SExportJobCreated:
    """Поставить фоновый экспорт таблицы в Excel."""
    job = await export_service.start(
        uow_session=uow_session, table_id=table_id, current_user=current_user
    )
    background_tasks.add_task(
        export_service.run, job.job_id, UnitOfWork(AsyncSessionFactory)
    )
    return job


@router.post(
    "/ws-ticket",
    response_model=SWsTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_ws_ticket(
    ticket_service: Annotated[WsTicketService, Depends(get_ws_ticket_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
) -> SWsTicketResponse:
    """Выдать одноразовый тикет для WebSocket-подключения к событиям таблицы."""
    return await ticket_service.issue(current_user)


@router.get("/", response_model=list[DataTableResponse])
async def get_tables(
    table_service: Annotated[TableService, Depends(get_table_service)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> list[DataTableResponse]:
    cache_key = tables_cache_key(current_user.user_id)
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    tables = await table_service.get_all_tables(
        uow_session, user_id=current_user.user_id, user_role=current_user.role
    )
    await redis.setex(
        cache_key,
        TABLES_CACHE_TTL,
        json.dumps([t.model_dump(mode="json") for t in tables]),
    )
    return tables


@router.get("/{table_id}", response_model=DataTableResponse)
async def get_table(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> DataTableResponse:
    return await table_service.get_table_by_id(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )


@router.patch("/{table_id}", response_model=DataTableResponse)
async def update_table(
    table_id: int,
    update_data: DataTableUpdate,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> DataTableResponse:
    result = await table_service.update_table(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
        update_data=update_data,
    )

    await invalidate_tables_cache(redis)
    return result


@router.post(
    "/create", response_model=DataTableResponse, status_code=status.HTTP_201_CREATED
)
async def create_table(
    table_data: DataTableCreate,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> DataTableResponse:
    result = await table_service.create_table(
        uow_session=uow_session, table_data=table_data, user_id=current_user.user_id
    )
    await invalidate_tables_cache(redis)
    return result


@router.post(
    "/{table_id}/duplicate",
    response_model=DataTableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_table(
    table_id: int,
    payload: DataTableDuplicate,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> DataTableResponse:
    result = await table_service.duplicate_table(
        uow_session=uow_session,
        source_table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
        with_rows=payload.with_rows,
        new_name=payload.name,
    )
    await invalidate_tables_cache(redis)
    return result


@router.post(
    "/process_excel",
    response_model=DataTableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_table_from_excel(
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    redis: Annotated[Redis, Depends(get_redis)],
    table_name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(default=None, description="Excel file to process"),  # noqa: B008
) -> DataTableResponse:
    result = await table_service.create_table_from_excel_file(
        uow_session=uow_session,
        excel_file=file,
        user_id=current_user.user_id,
        table_name=table_name,
        description=description,
    )
    await invalidate_tables_cache(redis)
    return result


@router.delete(
    "/delete/{table_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_table(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
):
    await table_service.delete_table(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await invalidate_tables_cache(redis)
    await invalidate_trash_cache(redis)


@router.post("/{table_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def pin_table(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> None:
    await table_service.pin_table(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await invalidate_tables_cache(redis)


@router.delete("/{table_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def unpin_table(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> None:
    await table_service.unpin_table(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await invalidate_tables_cache(redis)
