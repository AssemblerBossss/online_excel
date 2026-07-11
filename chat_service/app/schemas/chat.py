from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from datetime import datetime
from uuid import UUID


# Отправка сообщений (POST /chat/messages)
class MessageCreateRequest(BaseModel):
    receiver_email: EmailStr
    content: str

    # Валидация на уровне схемы. Не допускаем пустые сообщения или пробелы
    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Сообщение не может быть пустым")
        return v.strip()


# История сообщений(GET /chat/messages/{email})
class MessageOut(BaseModel):
    id: UUID
    sender_email: EmailStr
    content: str
    created_at: datetime
    is_read: bool

    model_config = ConfigDict(from_attributes=True)


# Список диалогов (GET /chat/users)
class DialogOut(BaseModel):
    # Здесь нет user1 и user2. Сервисный слой сам вычислит, с кем мы говорим
    interlocutor_email: EmailStr

    # Денормализованные данные из таблицы chats для быстрого рендера
    last_message_content: str | None
    last_message_at: datetime | None

    # Сервисный слой тоже вычислит, сколько непрочитанных у ТЕКУЩЕГО пользователя
    unread_count: int

    model_config = ConfigDict(from_attributes=True)


# Обертка для пагинации
class PaginatedResponse(BaseModel):
    items: list[MessageOut | DialogOut]
    total: int
    page: int | None = None
    cursor: str | None = None
