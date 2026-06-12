import json
from typing import Annotated
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from table_service.app.schemas import (
    DataTableCreate,
    DataTableResponse,
    SCurrentUser,
    DataTableUpdate,
    DataTableDuplicate,
)
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.services import TableService
from table_service.app.api.dependencies import (
    get_table_service,
    get_current_active_user,
    get_redis,
    get_async_uow_session,
)

from table_service.app.api.cache import (
    TABLES_CACHE_KEY,
    TRASH_CACHE_KEY,
    TABLES_CACHE_TTL,
    invalidate_tables_cache,
)


router = APIRouter()


@router.get("/", response_model=list[DataTableResponse])
async def get_tables(
    table_service: Annotated[TableService, Depends(get_table_service)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> list[DataTableResponse]:
    cached = await redis.get(TABLES_CACHE_KEY)
    if cached:
        return json.loads(cached)

    tables = await table_service.get_all_tables(uow_session)
    await redis.setex(
        TABLES_CACHE_KEY,
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
    file: UploadFile = File(..., description="Excel file to process"),
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


@router.get("/{table_id}/export")
async def export_table(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> StreamingResponse:
    """Скачать таблицу в формате Excel (.xlsx)."""
    workbook, filename = await table_service.export_table_to_excel(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    encoded = quote(filename)
    return StreamingResponse(
        workbook,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


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
    await redis.delete(TRASH_CACHE_KEY)
    return None
