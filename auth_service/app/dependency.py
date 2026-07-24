from typing import Annotated

from fastapi import Depends, HTTPException, Request

from auth_service.app.models import User as UserORM
from auth_service.app.schemas import SUserFilter, SUserInfo
from auth_service.app.services import AuthService, UserService
from auth_service.app.сore import UnitOfWork, get_async_uow_session


async def get_current_user(request: Request) -> SUserFilter:
    user_id = request.headers.get("X-User-ID")
    email = request.headers.get("X-User-Email")
    role = request.headers.get("X-User-Role")
    is_active = request.headers.get("X-User-Active")

    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return SUserFilter(
        id=int(user_id),
        email=email,
        role=role,
        is_active=is_active.lower() == "true" if is_active else False,
    )


async def get_current_active_user(
    current_user: Annotated[SUserFilter, Depends(get_current_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    async with uow_session.start():
        user: UserORM = await uow_session.user.find_one_or_none_by_id(current_user.id)
        if not user or not user.is_active:
            raise HTTPException(status_code=403, detail="Inactive user")
        return SUserInfo.model_validate(user)


def get_auth_service() -> AuthService:
    """Dependency для получения AuthService"""
    return AuthService()


def get_user_service() -> UserService:
    """Dependency для получения UserService"""
    return UserService()
