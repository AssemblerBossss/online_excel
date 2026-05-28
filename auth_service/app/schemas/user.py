from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
    field_validator,
)
from datetime import datetime
import enum

from auth_service.app.config import auth_service_settings


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class TokenRefresh(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str


class SUserFilter(BaseModel):
    id: int | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class EmailModel(BaseModel):
    email: EmailStr = Field(description="Электронная почта")
    model_config = ConfigDict(from_attributes=True)


class UserBase(EmailModel):
    first_name: str = Field(min_length=3, max_length=50)
    last_name: str = Field(min_length=3, max_length=50)


class SUserRegister(UserBase):
    password: str = Field(min_length=5, max_length=50)
    confirm_password: str = Field(min_length=5, max_length=50)

    @model_validator(mode="after")
    def check_password(self):
        if self.password != self.confirm_password:
            raise ValueError("Пароли не совпадают")
        return self


class SUserAddDB(UserBase):
    hashed_password: str = Field(
        min_length=5, description="Пароль в формате HASH-строки"
    )


class SUserAuth(EmailModel):
    password: str = Field(
        min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков"
    )


class SUserProfileUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=3, max_length=50)
    last_name: str | None = Field(default=None, min_length=3, max_length=50)


class SUserUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=3, max_length=50)
    last_name: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = None
    confirm_password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class SUserInfo(UserBase):
    id: int
    is_active: bool | None = None
    role: UserRole
    created_at: datetime
    avatar_url: str | None = Field(default=None, description="Ссылка на аватар")

    @field_validator("avatar_url")
    @classmethod
    def to_public_url(cls, v: str | None) -> str | None:
        if not v or v.startswith("http"):
            return v
        return f"{auth_service_settings.MINIO_PUBLIC_URL}/{auth_service_settings.MINIO_BUCKET}/{v}"
