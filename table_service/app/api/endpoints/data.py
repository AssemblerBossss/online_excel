import json
import logging
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    status,
)
from redis.asyncio import Redis

from table_service.app.api.dependencies import (
    get_async_uow_session,
    get_current_active_user,
    get_data_service,
    get_redis,
)
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.exceptions import ValidationException
from table_service.app.schemas import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    FilterOperator,
    PaginatedRows,
    RowFilter,
    SCurrentUser,
    TableRowCreate,
    TableRowResponse,
    TableRowUpdate,
)
from table_service.app.services import DataService

logger = logging.getLogger(__name__)
router = APIRouter()

ROWS_CACHE_TTL = 60


def _rows_cache_key(table_id: int) -> str:
    return f"rows:table:{table_id}"


def _parse_filters(raw: list[str] | None) -> list[RowFilter]:
    """Разобрать параметры вида `field:op:value` в список RowFilter."""
    filters: list[RowFilter] = []
    for item in raw or []:
        parts = item.split(":", 2)
        if len(parts) != 3:
            raise ValidationException(
                f"Неверный формат фильтра '{item}', ожидается field:op:value"
            )
        field, op, value = parts
        if op not in FilterOperator.__members__:
            raise ValidationException(f"Неизвестный оператор фильтра: '{op}'")
        filters.append(RowFilter(field=field, op=FilterOperator(op), value=value))
    return filters


@router.get(
    "/{table_id}/rows",
    response_model=PaginatedRows,
    status_code=status.HTTP_200_OK,
)
async def list_table_rows(
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    skip: int = Query(0, description="Количество пропускаемых строк", ge=0),
    limit: int = Query(100, description="Максимальное количество строк", ge=1, le=1000),
    sort_by: str | None = Query(None),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    filter: list[str] | None = Query(default=None, description="Фильтр в формате field:op:value (можно несколько)"
    ),
    table_id: int = Path(..., description="ID таблицы", ge=1),
):

    filters = _parse_filters(filter)
    # Кэшируем только дефолтный запрос (без пагинации и сортировки)
    use_cache = (
        skip == 0
        and limit == 100
        and sort_by is None
        and sort_order == "asc"
        and not filter
    )
    cache_key = _rows_cache_key(table_id)

    if use_cache:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

    result = await data_service.get_table_rows(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
    )

    if use_cache:
        await redis.setex(cache_key, ROWS_CACHE_TTL, result.model_dump_json())

    return result


@router.get(
    "/{table_id}/rows/{row_id}",
    response_model=TableRowResponse,
    status_code=status.HTTP_200_OK,
)
async def get_row(
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
) -> TableRowResponse | None:
    """Получить строку по ID"""
    return await data_service.get_table_row(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        row_id=row_id,
        user_role=current_user.role,
    )


@router.post(
    "/{table_id}/rows",
    response_model=TableRowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_table_row(
    row_data: TableRowCreate,
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(description="ID таблицы", ge=1),
) -> TableRowResponse:
    """Создать строку таблицы"""
    result = await data_service.create_table_row(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        row_data=row_data,
        user_role=current_user.role,
    )
    await redis.delete(_rows_cache_key(table_id))
    return result


@router.put(
    "/{table_id}/rows/{row_id}",
    response_model=TableRowResponse,
    status_code=status.HTTP_200_OK,
)
async def update_row(
    row_data: TableRowUpdate,
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
) -> TableRowResponse | None:
    """Обновить строку таблицы"""
    result = await data_service.update_table_row(
        uow_session=uow_session,
        table_id=table_id,
        row_id=row_id,
        user_id=current_user.user_id,
        row_data=row_data,
        user_role=current_user.role,
    )
    await redis.delete(_rows_cache_key(table_id))
    return result


@router.post(
    "/{table_id}/rows/bulk-delete",
    response_model=BulkDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def bulk_delete_rows(
    payload: BulkDeleteRequest,
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
) -> BulkDeleteResponse:
    """Удалить несколько строк одним запросом"""
    deleted_count = await data_service.bulk_delete_table_rows(
        uow_session=uow_session,
        table_id=table_id,
        row_ids=payload.row_ids,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await redis.delete(_rows_cache_key(table_id))
    return BulkDeleteResponse(deleted_count=deleted_count)


@router.delete("/{table_id}/rows/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_row(
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
):
    """Удалить строку таблицы"""
    await data_service.delete_table_row(
        uow_session=uow_session,
        table_id=table_id,
        row_id=row_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await redis.delete(_rows_cache_key(table_id))


@router.post(
    "/{table_id}/rows/{row_id}/duplicate",
    response_model=TableRowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_table_row(
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(description="ID таблицы", ge=1),
    row_id: int = Path(description="ID строки для копирования", ge=1),
) -> TableRowResponse:
    """Создать копию строки в той же таблице"""
    result = await data_service.duplicate_table_row(
        uow_session=uow_session,
        table_id=table_id,
        row_id=row_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await redis.delete(_rows_cache_key(table_id))
    return result
