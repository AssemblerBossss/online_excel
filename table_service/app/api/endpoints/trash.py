import json
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from redis.asyncio import Redis

from table_service.app.api.cache import (
    TABLES_CACHE_TTL,
    invalidate_tables_cache,
    invalidate_trash_cache,
    trash_cache_key,
)
from table_service.app.api.dependencies import (
    get_async_uow_session,
    get_current_active_user,
    get_redis,
    get_table_service,
)
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.schemas import (
    DataTableResponse,
    SCurrentUser,
)
from table_service.app.services import TableService

router = APIRouter()


@router.get("/", response_model=list[DataTableResponse])
async def get_trash(
    table_service: Annotated[TableService, Depends(get_table_service)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> list[DataTableResponse]:
    cache_key = trash_cache_key(current_user.user_id)
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    tables = await table_service.get_trash_tables(
        uow_session, user_id=current_user.user_id, user_role=current_user.role
    )
    await redis.setex(
        cache_key,
        TABLES_CACHE_TTL,
        json.dumps([t.model_dump(mode="json") for t in tables]),
    )
    return tables


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def permanent_delete(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> None:
    await table_service.permanent_delete_table(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await invalidate_trash_cache(redis)


@router.post("/{table_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_table_from_trash(
    table_id: int,
    table_service: Annotated[TableService, Depends(get_table_service)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> None:
    await table_service.restore_table(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    await invalidate_tables_cache(redis)  # основной список
    await invalidate_trash_cache(redis)
