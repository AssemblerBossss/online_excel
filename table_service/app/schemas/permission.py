from datetime import datetime
from pydantic import BaseModel
from pydantic.v1 import EmailStr


class TablePermissionCreate(BaseModel):
    email: EmailStr
    can_read: bool = False
    can_write: bool = False
    can_manage: bool = False


class TablePermissionUpdate(BaseModel):
    can_read: bool | None = None
    can_write: bool | None = None
    can_manage: bool | None = None


class TablePermissionResponse(BaseModel):
    id: int
    user_id: int
    user_email: EmailStr | None = None
    table_id: int
    can_read: bool
    can_write: bool
    can_manage: bool
    created_at: datetime

    model_config = {"from_attributes": True}
