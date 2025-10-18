from pydantic import BaseModel
from typing import Optional
from backend.app.models import UserRole


class UserBase(BaseModel):
    email: str
    hashed_password: str
    full_name: str
    role: UserRole = UserRole.VIEWER
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[str] = None
    hashed_password: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserFilter(BaseModel):
    id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
