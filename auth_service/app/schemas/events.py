from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


class UserEvent(BaseModel):
    """Базовое событие пользователя"""

    event_type: str
    user_id: int
    email: EmailStr
    role: str
    timestamp: datetime


class UserRegisterEvent(UserEvent):
    """Событие регистрации пользователя"""

    event_type: Literal["user.registered"] = "user.registered"


class UserUpdateEvent(UserEvent):
    """Событие обновления пользователя"""

    event_type: Literal["user.updated"] = "user.updated"
    old_email: str | None = None
    old_role: str | None = None


class UserDeletedEvent(BaseModel):
    """Событие удаления пользователя"""

    event_type: Literal["user.deleted"] = "user.deleted"
    user_id: int
    timestamp: datetime
