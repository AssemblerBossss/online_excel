from typing import List, Optional, Literal, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from backend.app.schemas import DataTableCreate, DataTableResponse
from backend.app.services import DataService


router = APIRouter(prefix="/tables", tags=["tables"])


@router.post(
    "/create", response_model=DataTableResponse, status_code=status.HTTP_201_CREATED
)
async def create_table(
    table_data: DataTableCreate,
    user: Annotated[UserSchema, Depends(get_current_user)],
    table_service: Annotated[table_service, Depends(table_service)],
) -> DataTableResponse:

    return await table_service.create_table(table_data=table_data, user_id=user.id)
