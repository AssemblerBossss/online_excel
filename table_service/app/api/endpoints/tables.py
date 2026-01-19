from typing import Annotated, List
from fastapi import (
    APIRouter,
    Depends,
    status,
    UploadFile,
    File,
    Form,
    Header,
)

from table_service.app.schemas import DataTableCreate, DataTableResponse
from table_service.app.services import TableService
from table_service.app.api.dependencies import get_table_service


router = APIRouter()


@router.get("/", response_model=List[DataTableResponse])
async def get_tables(
    table_service: Annotated[TableService, Depends(get_table_service)],
) -> List[DataTableResponse]:

    return await table_service.get_all_tables()


@router.post(
    "/create", response_model=DataTableResponse, status_code=status.HTTP_201_CREATED
)
async def create_table(
    table_data: DataTableCreate,
    table_service: Annotated[TableService, Depends(get_table_service)],
    x_user_id: int = Header(None, alias="X-User-ID"),
) -> DataTableResponse:

    return await table_service.create_table(table_data=table_data, user_id=x_user_id)


@router.post(
    "/process_excel",
    response_model=DataTableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_table_from_excel(
    table_service: Annotated[TableService, Depends(get_table_service)],
    x_user_id: int = Header(None, alias="X-User-ID"),
    table_name: str = Form(...),
    description: str = Form(None),  # Добавьте опциональное поле
    file: UploadFile = File(..., description="Excel file to process"),
) -> DataTableResponse:

    return await table_service.create_table_from_excel_file(
        excel_file=file,
        user_id=x_user_id,
        table_name=table_name,
        description=description,
    )


@router.delete(
    "/delete/{table_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_table(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    x_user_id: int = Header(None, alias="X-User-ID"),
    x_user_role: str = Header(None, alias="X-User-Role"),
    x_user_active: str = Header(None, alias="X-User-Active"),
):
    await table_service.delete_table(
        table_id=table_id, user_id=x_user_id, user_role=x_user_role
    )
    return None
