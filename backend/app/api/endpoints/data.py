from typing import List, Optional, Literal, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response

from backend.app.api import get_viewer_user, get_editor_user
from backend.app.schemas import (
    TableRowResponse,
    TableRowCreate,
    TableRowUpdate,
    TokenData,
)
from backend.app.services import DataService
from backend.app.api.dependencies import (
    get_data_service,
    get_table_service,
    get_user_service,
)


router = APIRouter()


@router.get("/{table_id}/rows", response_model=List[TableRowResponse])
async def list_table_rows(
    data_service: Annotated[DataService, Depends(get_data_service)],
    user: Annotated[TokenData, Depends(get_viewer_user)],
    skip: int = Query(0, description="Количество пропускаемых строк", ge=0),
    limit: int = Query(100, description="Максимальное количество строк", ge=1, le=1000),
    sort_by: Optional[str] = Query(None),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    table_id: int = Path(..., description="ID таблицы", ge=1),
):
    result: list[TableRowResponse] = await data_service.get_table_rows(
        table_id=table_id,
        user_id=user.id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return result


@router.get("/{table_id}/rows/{row_id}", response_model=TableRowResponse)
async def get_row(
    user: Annotated[TokenData, Depends(get_viewer_user)],
    data_service: Annotated[DataService, Depends(get_data_service)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
):
    """Получить строку по ID"""
    result = await data_service.get_table_row(
        table_id=table_id,
        user_id=user.id,
        row_id=row_id,
    )

    return result


@router.post(
    "/{table_id}/rows",
    response_model=TableRowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_table_row(
    user: Annotated[TokenData, Depends(get_editor_user)],
    row_data: TableRowCreate,
    data_service: Annotated[DataService, Depends(get_data_service)],
    table_id: int = Path(description="ID таблицы", ge=1),
):
    result = await data_service.create_table_row(
        table_id=table_id,
        user_id=user.id,
        row_data=row_data,
    )
    return result


@router.put("/{table_id}/rows/{row_id}", response_model=TableRowResponse)
async def update_row(
    row_data: TableRowUpdate,
    user: Annotated[TokenData, Depends(get_editor_user)],
    data_service: Annotated[DataService, Depends(get_data_service)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
):
    """Обновить строку таблицы"""
    result = await data_service.update_table_row(
        table_id=table_id,
        row_id=row_id,
        user_id=user.id,
        row_data=row_data,
    )
    return result


@router.delete("/{table_id}/rows/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_row(
    user: Annotated[TokenData, Depends(get_editor_user)],
    data_service: Annotated[DataService, Depends(get_data_service)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
):
    """Удалить строку таблицы"""
    await data_service.delete_table_row(
        table_id=table_id,
        row_id=row_id,
        user_id=user.id,
    )
