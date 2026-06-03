from typing import Annotated
from fastapi import APIRouter, Depends, status, UploadFile, File
from auth_service.app.schemas import SUserInfo
from auth_service.app.schemas.user import SUserProfileUpdate, SUserRoleUpdate
from auth_service.app.services import UserService
from auth_service.app.dependency import (
    get_current_active_user,
    get_user_service,
)
from auth_service.app.сore import get_async_uow_session, UnitOfWork
from auth_service.app.exceptions import UserNotFoundException

router = APIRouter()


@router.get("/me", response_model=SUserInfo)
async def read_users_me(
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
):
    return current_user


@router.get(
    "/{user_id}",
    response_model=SUserInfo,
    dependencies=[Depends(get_current_active_user)],
)
async def get_user_by_id(
    user_id: int,
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    """Получить пользователя по ID"""
    user = await user_service.get_user_by_id(uow_session=uow_session, user_id=user_id)
    if not user:
        raise UserNotFoundException()
    return user


@router.get(
    "/email/{email}",
    response_model=SUserInfo,
    dependencies=[Depends(get_current_active_user)],
)
async def get_user_by_email(
    email: str,
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    """Получить пользователя по email"""
    user = await user_service.get_user_by_email(uow_session=uow_session, email=email)
    if not user:
        raise UserNotFoundException()
    return user


@router.patch(
    "/{user_id}/role", response_model=SUserInfo, status_code=status.HTTP_200_OK
)
async def change_user_role(
    user_id: int,
    data: SUserRoleUpdate,
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    """Сменить роль пользователя (admin)"""
    user = await user_service.change_role(
        uow_session=uow_session,
        user_id=user_id,
        current_user=current_user,
        role=data.role,
    )
    if not user:
        raise UserNotFoundException()
    return user


@router.patch("/{user_id}", response_model=SUserInfo, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: int,
    data: SUserProfileUpdate,
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    """Обновить профиль пользователя"""
    user = await user_service.update_user(
        uow_session=uow_session, user_id=user_id, current_user=current_user, data=data
    )
    if not user:
        raise UserNotFoundException()
    return user


@router.delete(
    "/{user_id}/avatar",
    response_model=SUserInfo,
    status_code=status.HTTP_200_OK,
)
async def delete_avatar(
    user_id: int,
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> SUserInfo:
    """Удалить аватар пользователя"""
    user = await user_service.delete_avatar(
        uow_session=uow_session,
        current_user=current_user,
        user_id=user_id,
    )
    if not user:
        raise UserNotFoundException()
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> None:
    """Удалить пользователя по ID"""
    result = await user_service.delete_user(
        uow_session=uow_session, user_id=user_id, current_user=current_user
    )
    if not result:
        raise UserNotFoundException()


@router.post("/{user_id}/deactivate", response_model=SUserInfo)
async def deactivate_user(
    user_id: int,
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    """Деактивировать пользователя по ID"""
    user = await user_service.deactivate_user(
        uow_session=uow_session, current_user=current_user, user_id=user_id
    )
    if not user:
        raise UserNotFoundException()
    return user


@router.post("/{user_id}/activate}", response_model=SUserInfo)
async def activate_user(
        user_id: int,
        current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
        user_service: Annotated[UserService, Depends(get_user_service)],
        uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    """Активировать пользователя по ID"""
    user = await user_service.activate_user(
        uow_session=uow_session,current_user=current_user, user_id=user_id)
    if not user:
        raise UserNotFoundException()
    return user


@router.get(
    "/all_users/",
    response_model=list[SUserInfo],
    dependencies=[Depends(get_current_active_user)],
)
async def get_all_users(
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> list[SUserInfo]:
    """Получить список всех пользователей"""
    return await user_service.get_all_users(uow_session=uow_session)


@router.post("/{user_id}/avatar", response_model=SUserInfo)
async def upload_avatar(
    user_id: int,
    file: Annotated[UploadFile, File(...)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Обновить аватар пользователя"""
    content = await file.read()
    user = await user_service.update_avatar(
        uow_session=uow_session,
        current_user=current_user,
        user_id=user_id,
        content=content,
        content_type=file.content_type,
    )
    if not user:
        raise UserNotFoundException()
    return user
