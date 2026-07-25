import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from jose import jwt

from auth_service.app.config import auth_service_settings


@lru_cache(maxsize=1)
def _private_key() -> str:
    return Path(auth_service_settings.JWT_PRIVATE_KEY_PATH).read_text()


@lru_cache(maxsize=1)
def _public_key() -> str:
    return Path(auth_service_settings.JWT_PUBLIC_KEY_PATH).read_text()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Создает JWT Access Token"""

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=auth_service_settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(UTC),
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
