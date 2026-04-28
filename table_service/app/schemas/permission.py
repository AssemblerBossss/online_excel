from datetime import datetime
from pydantic import BaseModel


class TablePermissionCreate(BaseModel):
    user_id: int
    can_read: bool = False
    can_write: bool = False
    can_manage: bool = False


class TablePermissionResponse(BaseModel):
    id: int
    user_id: int
    table_id: int
    can_read: bool
    can_write: bool
    can_manage: bool
    created_at: datetime

    model_config = {"from_attributes": True}
