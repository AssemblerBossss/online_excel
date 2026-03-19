from typing import Annotated
from fastapi import APIRouter, Depends, status
from auth_service.app.schemas import SUserInfo
from auth_service.app.services import UserService
from auth_service.app.dependency import (
    get_current_active_user,
    get_user_service,
)
from auth_service.app.сore import get_async_uow_session, UnitOfWork
from auth_service.app.exceptions import UserNotFoundException

router = APIRouter()


@router.get("/users/{user_id}", response_model=SUserInfo)
async def get_user_by_id(
    user_id: int,
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    """Получить пользователя по ID"""
    user = await user_service.get_user_by_id(uow_session=uow_session, user_id=user_id)
    if not user:
        raise UserNotFoundException()
    return user


@router.get("/users/email/{email}", response_model=SUserInfo)
async def get_user_by_email(
    email: str,
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    """Получить пользователя по email"""
    user = await user_service.get_user_by_email(uow_session=uow_session, email=email)
    if not user:
        raise UserNotFoundException()
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> None:
    """Удалить пользователя по ID"""
    result = await user_service.delete_user(uow_session=uow_session, user_id=user_id)
    if not result:
        raise UserNotFoundException()


@router.post("/users/{user_id}/deactivate", response_model=SUserInfo)
async def deactivate_user(
    user_id: int,
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    """Деактивировать пользователя по ID"""
    user = await user_service.deactivate_user(uow_session=uow_session, user_id=user_id)
    if not user:
        raise UserNotFoundException()
    return user


@router.get("/all_users/", response_model=list[SUserInfo])
async def get_all_users(
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> list[SUserInfo]:
    return await user_service.get_all_users(uow_session=uow_session)


@router.get("/users/me")
async def read_users_me(
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
):
    return current_user
