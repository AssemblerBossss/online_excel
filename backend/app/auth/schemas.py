import re
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator, computed_field
from backend.app.auth.utils import get_password_hash


class EmailModel(BaseModel):
    email: EmailStr = Field(description="Электронная почта")
    model_config = ConfigDict(from_attributes=True)


class UserBase(EmailModel):
    phone_number: str = Field(description="Номер телефона в международном формате, начинающийся с '+'")
    first_name: str = Field(min_length=3, max_length=50, description="Имя, от 3 до 50 символов")
    last_name: str = Field(min_length=3, max_length=50, description="Фамилия, от 3 до 50 символов")

    @field_validator("phone_number")
    def validate_phone_number(cls, value: str) -> str:
        if not re.match(r'^\+\d{5,15}$', value):
            raise ValueError('Номер телефона должен начинаться с "+" и содержать от 5 до 15 цифр')
        return value


class SUserRegister(UserBase):
    password: str = Field(min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")
    confirm_password: str = Field(min_length=5, max_length=50, description="Повторите пароль")

    @model_validator(mode="after")
    def check_password(self):
        if self.password != self.confirm_password:
            raise ValueError("Пароли не совпадают")
        #self.password = get_password_hash(self.password)  # хешируем пароль до сохранения в базе данных
        return self


class SUserAddDB(UserBase):
    password: str = Field(min_length=5, description="Пароль в формате HASH-строки")


class SUserAuth(EmailModel):
    password: str = Field(min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")


class RoleModel(BaseModel):
    id: int = Field(description="Идентификатор роли")
    name: str = Field(description="Название роли")
    model_config = ConfigDict(from_attributes=True)


class SUserInfo(UserBase):
    id: int = Field(description="Идентификатор пользователя")
    role: RoleModel = Field(exclude=True)

    @computed_field
    def role_name(self) -> str:
        return self.role.name

    @computed_field
    def role_id(self) -> int:
        return self.role.id
