from fastapi import Request, Depends, HTTPException
from fastapi.responses import Response
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession


from backend.app.schemas import TokenData
from backend.app.models import User, UserRole
from backend.app.repository import UserRepository
from backend.app.core import app_settings
from backend.app.dependencies import get_session_without_commit
from backend.app.exceptions import (
    TokenNoFound,
    NoJwtException,
    TokenExpiredException,
    NoUserIdException,
    ForbiddenException,
    UserNotFoundException,
)


def create_tokens(data: dict) -> dict:
    # Текущее время в UTC
    now = datetime.now(timezone.utc)

    # AccessToken - 30 минут
    access_expire = now + timedelta(seconds=10)
    access_payload = data.copy()
    access_payload.update({"exp": int(access_expire.timestamp()), "type": "access"})
    access_token = jwt.encode(
        access_payload,
        app_settings.JWT_SECRET_KEY,
        algorithm=app_settings.JWT_ALGORITHM,
    )

    # RefreshToken - 7 дней
    refresh_expire = now + timedelta(days=7)
    refresh_payload = data.copy()
    refresh_payload.update({"exp": int(refresh_expire.timestamp()), "type": "refresh"})
    refresh_token = jwt.encode(
        refresh_payload,
        app_settings.JWT_SECRET_KEY,
        algorithm=app_settings.JWT_ALGORITHM,
    )
    return {"access_token": access_token, "refresh_token": refresh_token}


def set_tokens(response: Response, user_id: int):
    new_tokens = create_tokens(data={"sub": str(user_id)})
    access_token = new_tokens.get("access_token")
    refresh_token = new_tokens.get("refresh_token")

    response.set_cookie(
        key="user_access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    response.set_cookie(
        key="user_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
    )


def get_access_token(request: Request) -> str:
    """Извлекаем access_token из кук."""
    token = request.cookies.get("user_access_token")
    if not token:
        raise TokenNoFound
    return token


def get_refresh_token(request: Request) -> str:
    """Извлекаем refresh_token из кук."""
    token = request.cookies.get("user_refresh_token")
    if not token:
        raise TokenNoFound
    return token


async def check_refresh_token(
    token: str = Depends(get_refresh_token),
    session: AsyncSession = Depends(get_session_without_commit),
) -> User:
    """Проверяем refresh_token и возвращаем пользователя."""
    try:
        payload = jwt.decode(
            token, app_settings.JWT_SECRET_KEY, algorithms=[app_settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise NoJwtException

        user = await UserRepository(session).find_one_or_none_by_id(
            user_id=int(user_id)
        )
        if not user:
            raise NoJwtException

        return user
    except JWTError:
        raise NoJwtException


async def get_current_user(
    token: str = Depends(get_access_token),
    session: AsyncSession = Depends(get_session_without_commit),
) -> User:
    """Проверяем access_token и возвращаем пользователя."""
    try:
        # Декодируем токен
        payload = jwt.decode(
            token, app_settings.JWT_SECRET_KEY, algorithms=[app_settings.JWT_ALGORITHM]
        )
    except ExpiredSignatureError:
        raise TokenExpiredException
    except JWTError:
        # Общая ошибка для токенов
        raise NoJwtException

    expire: str = payload.get("exp")
    expire_time = datetime.fromtimestamp(int(expire), tz=timezone.utc)
    if (not expire) or (expire_time < datetime.now(timezone.utc)):
        raise TokenExpiredException

    user_id: str = payload.get("sub")
    if not user_id:
        raise NoUserIdException

    user = await UserRepository(session).find_one_or_none_by_id(user_id=int(user_id))
    if not user:
        raise UserNotFoundException
    return user


async def get_admin_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def get_editor_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    if current_user.role not in [UserRole.ADMIN, UserRole.EDITOR]:
        raise HTTPException(status_code=403, detail="Editor access required")
    return current_user


async def get_viewer_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    return current_user
