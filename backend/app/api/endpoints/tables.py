from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

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


@router.post(
    "/process_excel",
    response_model=DataTableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_table_from_excel(
    user: Annotated[TokenData, Depends(get_admin_user)],
    table_service: Annotated[TableService, Depends(get_table_service)],
    table_name: str = Form(...),
    file: UploadFile = File(..., description="Excel file to process"),
) -> DataTableResponse:

    return await table_service.create_table_from_excel_file(
        excel_file=file, user_id=user.id, table_name=table_name
    )
