from typing import Annotated
from fastapi import APIRouter, Depends, status

from table_service.app.schemas import (
    TablePermissionCreate,
    TablePermissionResponse,
    SCurrentUser,
    TablePermissionUpdate,
)
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.services import PermissionService
from table_service.app.api.dependencies import (
    get_permission_service,
    get_current_active_user,
    get_async_uow_session,
)

router = APIRouter()


@router.get(
    "/", response_model=list[TablePermissionResponse], status_code=status.HTTP_200_OK
)
async def get_permissions(
    table_id: int,
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> list[TablePermissionResponse]:
    return await permission_service.get_permissions(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )


@router.post(
    "/", response_model=TablePermissionResponse, status_code=status.HTTP_201_CREATED
)
async def create_permission(
    table_id: int,
    data: TablePermissionCreate,
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> TablePermissionResponse:
    return await permission_service.create_permission(
        uow_session=uow_session,
        table_id=table_id,
        data=data,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )


@router.patch(
    "/{target_user_id}",
    response_model=TablePermissionResponse,
    status_code=status.HTTP_200_OK,
)
async def update_permission(
    table_id: int,
    target_user_id: int,
    data: TablePermissionUpdate,
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> TablePermissionResponse:
    return await permission_service.update_permission(
        uow_session=uow_session,
        table_id=table_id,
        target_user_id=target_user_id,
        data=data,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )


@router.delete("/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    table_id: int,
    target_user_id: int,
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
):
    await permission_service.delete_permission(
        uow_session=uow_session,
        table_id=table_id,
        target_user_id=target_user_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )
    return None
