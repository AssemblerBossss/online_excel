from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, EmailStr, Field


class BaseEvent(BaseModel):
    """Базовый класс для всех событий."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    timestamp: datetime


class UserEvent(BaseEvent):
    """Базовое событие пользователя."""

    user_id: int
    email: EmailStr
    role: str


class UserRegisterEvent(UserEvent):
    event_type: Literal["user.registered"] = "user.registered"
    first_name: str | None = None


class UserUpdateEvent(UserEvent):
    event_type: Literal["user.updated"] = "user.updated"
    old_email: str | None = None
    old_role: str | None = None


class UserDeletedEvent(BaseEvent):
    event_type: Literal["user.deleted"] = "user.deleted"
    user_id: int
