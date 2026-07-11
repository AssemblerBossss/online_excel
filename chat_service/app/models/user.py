from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import mapped_column, Mapped
from datetime import datetime
from chat_service.app.core import Base


class ChatUser(Base):
    __tablename__ = "chat_users"

    id = Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
