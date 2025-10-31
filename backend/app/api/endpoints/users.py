from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repository import UserRepository
from backend.app.schemas import SUserInfo
from backend.app.services import UserService
from backend.app.api.jwt_utils import get_current_user, get_admin_user
from backend.app.dependencies.database_dependencies import get_session_with_commit
from backend.app.models import User

router = APIRouter()


@router.get("/me/")
async def get_me(user_data: User = Depends(get_current_user)) -> SUserInfo:
    return await UserService(None).get_me(user_data)


@router.get("/all_users/", response_model=list[SUserInfo])
async def get_all_users(
    session: AsyncSession = Depends(get_session_with_commit),
    user_data: User = Depends(get_admin_user),
) -> List[SUserInfo]:
    return await UserService(session).get_all_users()
