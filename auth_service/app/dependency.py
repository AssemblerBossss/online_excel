from fastapi import Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.app.services import AuthService
from auth_service.app.сore.database import get_db

from typing import Annotated
from auth_service.app.сore import UnitOfWork
from auth_service.app.models import User as UserORM
from auth_service.app.schemas import SUserInfo, SUserFilter


async def get_current_user(request: Request) -> SUserFilter:
    payload = getattr(request.state, "user", None)
    if payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return SUserFilter(**payload)


async def get_current_active_user(
    payload: Annotated[dict, Depends(get_current_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> SUserInfo:
    async with uow_session:
        user: UserORM = await uow_session.auth.find_one_or_none_by_id(
            int(payload["user_id"])
        )
        if not user or not user.is_active:
            raise HTTPException(status_code=403, detail="Inactive user")
        return SUserInfo.model_validate(user)


def get_auth_service(session: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    """Dependency для получения AuthService"""
    return AuthService(session)
