import secrets
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError

from auth_service.app.config import auth_service_settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создает JWT Access Token"""

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=auth_service_settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "sub": str(data["user_id"]),
            "email": data["email"],
            "role": data["role"],
            "is_active": data.get("is_active", True),
            "token_type": "access",
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        key=auth_service_settings.JWT_SECRET_KEY,
        algorithm=auth_service_settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token() -> str:
    """Создает случайный Refresh Token"""
    return secrets.token_urlsafe(48)


def verify_access_token(token: str) -> dict:
    """Проверяет и декодирует JWT Access Token"""
    payload = jwt.decode(
        token,
        auth_service_settings.JWT_SECRET_KEY,
        algorithms=[auth_service_settings.JWT_ALGORITHM],
    )
    return payload
