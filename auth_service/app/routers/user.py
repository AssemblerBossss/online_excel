from typing import List, Annotated
from fastapi import APIRouter, Depends
from auth_service.app.schemas import SUserInfo
from auth_service.app.services import UserService

from auth_service.app.dependency import get_current_user, get_current_active_user
from auth_service.app.models import User

router = APIRouter()

# @router.get("/all_users/", response_model=list[SUserInfo])
# async def get_all_users(
#     session: AsyncSession = Depends(get_session_with_commit),
#     user_data: User = Depends(get_admin_user),
# ) -> List[SUserInfo]:
#     return await UserService(session).get_all_users()


@router.get("/users/me")
async def read_users_me(
    current_user: Annotated[SUserInfo, Depends(get_current_active_user)],
):
    return current_user
