from typing import Annotated
from fastapi import APIRouter, Response, Depends
from starlette import status

from backend.app.api.dependencies import get_user_service, get_auth_service
from backend.app.models import User
from backend.app.api.jwt_utils import set_tokens

from backend.app.api.jwt_utils import (
    get_current_user,
    get_admin_user,
    check_refresh_token,
)
from backend.app.schemas.user import (
    SUserRegister,
    SUserAuth,
    SUserInfo,
    SUserFilter,
    SUserAddDB,
)
from backend.app.services import UserService, AuthService

router = APIRouter()


@router.post("/register/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: SUserRegister, auth_service: Annotated[AuthService, get_auth_service]
):
    await auth_service.register_user(user_data)


@router.post("/login/", response_model=dict)
async def auth_user(
    response: Response,
    user_data: SUserAuth,
    auth_service: Annotated[AuthService, get_auth_service],
):
    return await auth_service.login_user(response=response, user_data=user_data)


@router.post("/logout", response_model=dict)
async def logout(
    response: Response, auth_service: Annotated[AuthService, get_auth_service]
):
    return await auth_service.logout(response=response)


@router.post("/refresh")
async def process_refresh_token(
    response: Response,
    auth_service: Annotated[AuthService, get_auth_service],
    user: User = Depends(check_refresh_token),
):
    await auth_service.refresh_tokens(response=response, user_id=user.id)
