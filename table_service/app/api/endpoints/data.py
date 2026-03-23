import logging
from typing import Annotated, Literal
from fastapi import (
    APIRouter,
    Depends,
    status,
    Query,
    Path,
)
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache

from table_service.app.schemas import (
    TableRowResponse,
    TableRowCreate,
    TableRowUpdate,
    SCurrentUser,
)
from table_service.app.services import DataService
from table_service.app.api.dependencies import get_data_service, get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{table_id}/rows", response_model=list[TableRowResponse])
@cache(expire=60, namespace="rows")
async def list_table_rows(
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    skip: int = Query(0, description="Количество пропускаемых строк", ge=0),
    limit: int = Query(100, description="Максимальное количество строк", ge=1, le=1000),
    sort_by: str | None = Query(None),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    table_id: int = Path(..., description="ID таблицы", ge=1),
):
    return await data_service.get_table_rows(
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{table_id}/rows/{row_id}", response_model=TableRowResponse)
@cache(expire=120, namespace="rows")
async def get_row(
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
) -> TableRowResponse | None:
    """Получить строку по ID"""
    return await data_service.get_table_row(
        table_id=table_id,
        user_id=current_user.user_id,
        row_id=row_id,
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
    table_id: int = Path(description="ID таблицы", ge=1),
) -> TableRowResponse:
    """Создать строку таблицы"""
    result = await data_service.create_table_row(
        table_id=table_id,
        user_id=current_user.user_id,
        row_data=row_data,
    )
    await FastAPICache.clear(namespace="rows")
    return result


@router.put("/{table_id}/rows/{row_id}", response_model=TableRowResponse)
async def update_row(
    row_data: TableRowUpdate,
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
) -> TableRowResponse | None:
    """Обновить строку таблицы"""
    result = await data_service.update_table_row(
        table_id=table_id,
        row_id=row_id,
        user_id=current_user.user_id,
        row_data=row_data,
    )
    await FastAPICache.clear(namespace="rows")
    return result


@router.delete("/{table_id}/rows/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_row(
    data_service: Annotated[DataService, Depends(get_data_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
):
    """Удалить строку таблицы"""
    await data_service.delete_table_row(
        table_id=table_id,
        row_id=row_id,
        user_id=current_user.user_id,
    )
    await FastAPICache.clear(namespace="rows")
    logger.info("Cache cleared for namespace 'rows', table_id=%s", table_id)

