from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing import Optional
from datetime import datetime
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


# OAuth2 Schemas
class TokenData(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool


class TokenRefresh(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str


class SUserFilter(BaseModel):
    id: Optional[int] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class EmailModel(BaseModel):
    email: EmailStr = Field(description="Электронная почта")
    model_config = ConfigDict(from_attributes=True)


class UserBase(EmailModel):
    first_name: str = Field(
        min_length=3, max_length=50, description="Имя, от 3 до 50 символов"
    )
    last_name: str = Field(
        min_length=3, max_length=50, description="Фамилия, от 3 до 50 символов"
    )


class SUserRegister(UserBase):
    password: str = Field(
        min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков"
    )
    confirm_password: str = Field(
        min_length=5, max_length=50, description="Повторите пароль"
    )

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


class SUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class SUserInfo(UserBase):
    id: int = Field(description="Идентификатор пользователя")
    is_active: Optional[bool] = None
    role: UserRole = Field(description="Роль пользователя")
    created_at: datetime = Field(description="Дата регистрации")
