from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from table_service.app.schemas import DataTableCreate, DataTableResponse, SCurrentUser
from table_service.app.services import TableService
from table_service.app.api.dependencies import (
    get_table_service,
    get_current_active_user,
)

router = APIRouter()


@router.get("/", response_model=list[DataTableResponse])
@cache(expire=120, namespace="tables")
async def get_tables(
    table_service: Annotated[TableService, Depends(get_table_service)],
) -> list[DataTableResponse]:
    return await table_service.get_all_tables()


@router.get("/{table_id}", response_model=DataTableResponse)
async def get_table(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
) -> DataTableResponse:
    return await table_service.get_table_by_id(
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )


@router.post(
    "/create", response_model=DataTableResponse, status_code=status.HTTP_201_CREATED
)
async def create_table(
    table_data: DataTableCreate,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
) -> DataTableResponse:
    result = await table_service.create_table(
        table_data=table_data, user_id=current_user.user_id
    )
    await FastAPICache.clear(namespace="tables")
    return result


@router.post(
    "/process_excel",
    response_model=DataTableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_table_from_excel(
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    table_name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(..., description="Excel file to process"),
) -> DataTableResponse:
    result = await table_service.create_table_from_excel_file(
        excel_file=file,
        user_id=current_user.user_id,
        table_name=table_name,
        description=description,
    )
    await FastAPICache.clear(namespace="tables")
    return result


@router.delete(
    "/delete/{table_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_table(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
):
    await table_service.delete_table(
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await FastAPICache.clear(namespace="tables")
    await FastAPICache.clear(namespace="rows")
    return None
