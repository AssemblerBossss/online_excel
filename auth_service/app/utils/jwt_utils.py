import secrets
from functools import lru_cache
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import jwt

from auth_service.app.config import auth_service_settings


@lru_cache(maxsize=1)
def _private_key() -> str:
    return Path(auth_service_settings.JWT_PRIVATE_KEY_PATH).read_text()


@lru_cache(maxsize=1)
def _public_key() -> str:
    return Path(auth_service_settings.JWT_PUBLIC_KEY_PATH).read_text()


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
        key=_private_key(),
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
        _public_key(),
        algorithms=[auth_service_settings.JWT_ALGORITHM],
    )
    return payload
