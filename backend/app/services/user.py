from datetime import datetime, timezone
from fastapi import Request, Depends
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

# from backend.app.auth.dao import UsersDAO
# from backend.app.auth.models import User
from backend.app.models import User
from backend.app.repository import UserRepository

from backend.app.config import settings
from backend.app.dependencies import get_session_without_commit
from backend.app.exceptions import (
    TokenNoFound,
    NoJwtException,
    TokenExpiredException,
    NoUserIdException,
    ForbiddenException,
    UserNotFoundException,
)


class UserService:
    pass
