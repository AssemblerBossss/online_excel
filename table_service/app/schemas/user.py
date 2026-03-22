from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SUserFilter(BaseModel):
    """Данные пользователя из JWT payload (request.state.user)"""

    user_id: int
    email: str
    role: str
    is_active: bool


class SCurrentUser(BaseModel):
    """Данные пользователя из БД (UserProjection)"""

    user_id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
