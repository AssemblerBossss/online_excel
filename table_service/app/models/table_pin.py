from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from table_service.app.core import Base


class TablePin(Base):
    """Закрепление таблицы конкретным пользователем"""

    __tablename__ = "table_pins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),  # ← Добавлен FK
        nullable=False,
    )
    table_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_tables.id", ondelete="CASCADE"), nullable=False
    )
    pinned_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "table_id", name="uq_table_pins_user_table"),
        Index("ix_table_pins_user_id", "user_id"),
        # Индекс на table_id тоже не помешает
        Index("ix_table_pins_table_id", "table_id"),
    )
