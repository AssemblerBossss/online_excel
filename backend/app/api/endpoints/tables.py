from typing import List, Optional, Literal, Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api import get_admin_user
from backend.app.schemas import DataTableCreate, DataTableResponse, TokenData
from backend.app.services import DataService, TableService
from backend.app.api.dependencies import get_table_service, get_table_repository


router = APIRouter()


@router.post(
    "/create", response_model=DataTableResponse, status_code=status.HTTP_201_CREATED
)
async def create_table(
    table_data: DataTableCreate,
    user: Annotated[TokenData, Depends(get_admin_user)],
    table_service: Annotated[TableService, Depends(get_table_service)],
) -> DataTableResponse:

    return await table_service.create_table(table_data=table_data, user_id=user.id)
