from typing import List, Optional, Literal, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

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


router = APIRouter(prefix="/data", tags=["data"])


@router.get("{table_id}/rows", response_model=List[TableRowResponse])
async def list_table_rows(
    data_service: Annotated[DataService, Depends(get_data_service)],
    user: Annotated[TokenData, Depends(get_viewer_user)],
    skip: int = Query(0, description="Количество пропускаемых строк", ge=0),
    limit: int = Query(100, description="Максимальное количество строк", ge=1, le=1000),
    sort_by: Optional[str] = Query(None),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    table_id: int = Path(..., description="ID таблицы", ge=1),
):
    pass


@router.get("/{table_id}/rows/{row_id}", response_model=TableRowResponse)
async def get_row(
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
    # user: Annotated[UserSchema, Depends(get_current_user)],
    # data_service: Annotated[TaskService, Depends(get_task_service)],
):
    """Получить строку по ID"""
    pass


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
    result = data_service.create_table_row(
        table_id=table_id,
        user_id=user.id,
        row_data=row_data,
    )
    return result


@router.put("/{table_id}/rows/{row_id}", response_model=TableRowResponse)
async def update_row(
    row_data: TableRowUpdate,
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
    # user: Annotated[UserSchema, Depends(get_current_user)],
    # data_service: Annotated[TaskService, Depends(get_task_service)],
):
    """Обновить строку таблицы"""
    pass


@router.delete("/{table_id}/rows/{row_id}")
async def delete_row(
    table_id: int = Path(..., description="ID таблицы", ge=1),
    row_id: int = Path(..., description="ID строки", ge=1),
    # user: Annotated[UserSchema, Depends(get_current_user)],
    # data_service: Annotated[TaskService, Depends(get_task_service)],
):
    """Удалить строку таблицы"""
    pass
