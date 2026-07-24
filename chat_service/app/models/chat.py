import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chat_service.app.core import Base


class Chat(Base):
    __tablename__ = "chats"

    # Уникальный constrain для защиты от дубликатов диалогов
    __table_args__ = (
        UniqueConstraint("user1_email", "user2_email", name="uq_chat_users_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )
    # Сортированная пара: тот, чей email меньше по алфавиту, всегда user1
    user1_email: Mapped[str] = mapped_column(
        String(255), ForeignKey("chat_users.email"), nullable=False
    )
    user2_email: Mapped[str] = mapped_column(
        String(255), ForeignKey("chat_users.email"), nullable=False
    )

    # Денормализация для быстрого отображения списка чатов
    last_message_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Счетчики непрочитанных для каждого участника
    unread_count_user1: Mapped[int] = mapped_column(default=0, nullable=False)
    unread_count_user2: Mapped[int] = mapped_column(default=0, nullable=False)

    # Связь с сообщениями (удобно для каскадного удаления, если это понадобится)
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    __table_args__ = (
        Index(
            "idx_message_chat_created", "chat_id", "created_at"
        ),  # Для быстрой пагинации
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )

    # Храним реальных отправителя и получателя (без сортировки!)
    sender_email: Mapped[str] = mapped_column(
        String(255), ForeignKey("chat_users.email"), nullable=False
    )
    receiver_email: Mapped[str] = mapped_column(
        String(255), ForeignKey("chat_users.email"), nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Обратная связь
    chat: Mapped["Chat"] = relationship(back_populates="messages")
