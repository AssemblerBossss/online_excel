from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

if TYPE_CHECKING:
    from table_service.app.models.data import TableRow

from table_service.app.core import Base


class DataTable(Base):
    __tablename__ = "data_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    columns_schema: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    created_by_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    permissions: Mapped[list[TablePermission]] = relationship(
        "TablePermission", back_populates="table", cascade="all, delete-orphan"
    )
    rows: Mapped[list[TableRow]] = relationship(
        "TableRow", back_populates="table", cascade="all, delete-orphan"
    )

    # Для помещения в корзину
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    deleted_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TablePermission(Base):
    __tablename__ = "table_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("data_tables.id", ondelete="CASCADE"),  # ← Добавить ondelete
        nullable=False,
    )

    can_read: Mapped[bool] = mapped_column(Boolean, default=False)
    can_write: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    table: Mapped[DataTable] = relationship("DataTable", back_populates="permissions")
