import json
from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    status,
    UploadFile,
    File,
    Form,
)
from redis.asyncio import Redis

from table_service.app.schemas import (
    DataTableCreate,
    DataTableResponse,
    SCurrentUser,
    DataTableUpdate,
    DataTableDuplicate,
)
from table_service.app.services import TableService
from table_service.app.api.dependencies import (
    get_table_service,
    get_current_active_user,
    get_redis,
)

router = APIRouter()

TABLES_CACHE_KEY = "tables:all"
TABLES_CACHE_TTL = 120


async def invalidate_tables_cache(redis: Redis) -> None:
    await redis.delete(TABLES_CACHE_KEY)


@router.get("/", response_model=list[DataTableResponse])
async def get_tables(
    table_service: Annotated[TableService, Depends(get_table_service)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> list[DataTableResponse]:
    cached = await redis.get(TABLES_CACHE_KEY)
    if cached:
        return json.loads(cached)

    tables = await table_service.get_all_tables()
    await redis.setex(
        TABLES_CACHE_KEY,
        TABLES_CACHE_TTL,
        json.dumps([t.model_dump(mode="json") for t in tables]),
    )
    return tables


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


@router.patch("/{table_id}", response_model=DataTableResponse)
async def update_table(
    table_id: int,
    update_data: DataTableUpdate,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> DataTableResponse:
    result = await table_service.update_table(
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
        update_data=update_data,
    )

    await invalidate_tables_cache(redis)
    return result


@router.post(
    "/create", response_model=DataTableResponse, status_code=status.HTTP_201_CREATED
)
async def create_table(
    table_data: DataTableCreate,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> DataTableResponse:
    result = await table_service.create_table(
        table_data=table_data, user_id=current_user.user_id
    )
    await invalidate_tables_cache(redis)
    return result


@router.post(
    "/{table_id}/duplicate",
    response_model=DataTableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_table(
    table_id: int,
    payload: DataTableDuplicate,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> DataTableResponse:
    result = await table_service.duplicate_table(
        table_id=table_id, payload=payload, user_id=current_user.user_id
    )
    await invalidate_tables_cache(redis)
    return result


@router.post(
    "/process_excel",
    response_model=DataTableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_table_from_excel(
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
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
    await invalidate_tables_cache(redis)
    return result


@router.delete(
    "/delete/{table_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_table(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    await table_service.delete_table(
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await invalidate_tables_cache(redis)
    return None
