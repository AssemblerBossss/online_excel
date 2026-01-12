from typing import Optional
from fastapi import HTTPException, status
from jose import jwt, JWTError
from pydantic import BaseModel
from api_gateway.app.config import settings


class UserData(BaseModel):
    user_id: int
    email: str
    role: str
    is_active: bool


def verify_jwt_token(token: str) -> Optional[UserData]:
    """
    Проверяет JWT токен и возвращает данные пользователя
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token=token,
            key=settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: int = int(payload.get("user_id"))
        email: str = payload.get("email")
        role: str = payload.get("role")
        is_active: bool = payload.get("is_active")

        if user_id is None or email is None:
            raise credentials_exception

        return UserData(
            user_id=user_id,
            email=email,
            role=role,
            is_active=is_active,
        )
    except (JWTError, ValueError, TypeError) as e:
        raise credentials_exception


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Извлекает токен из заголовка Authorization

    Args:
        authorization: Заголовок вида "Bearer <token>"

    Returns:
        JWT токен или None
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
