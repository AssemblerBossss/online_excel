from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from backend.app.schemas import TableRowResponse, TableRowCreate, TableRowUpdate


router = APIRouter(prefix="/data", tags=["data"])


@router.get("{table_id}/rows", response_model=List[TableRowResponse])
async def list_table_rows(
    skip: int = Query(0, description="Количество пропускаемых строк", ge=0),
    limit: int = Query(100, description="Максимальное количество строк", ge=1, le=1000),
    sort_by: Optional[str] = Query(None),
    table_id: int = Path(..., description="ID таблицы", ge=1),
    # data_service: Annotated[TaskService, Depends(get_task_service)],
    # user: Annotated[UserSchema, Depends(get_current_active_auth_user)],
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


@router.post("/{table_id}/rows", response_model=TableRowResponse)
async def create_table_row(
    row_data: TableRowCreate,
    # user: Annotated[UserSchema, Depends(get_current_user)],
    # data_service: Annotated[TaskService, Depends(get_task_service)],
):
    pass


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
