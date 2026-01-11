from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.app.services import AuthService
from auth_service.app.database import get_db


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency для получения AuthService"""
    return AuthService(session)
