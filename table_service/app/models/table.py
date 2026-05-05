from __future__ import annotations
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional, TYPE_CHECKING, List, Dict, Any

if TYPE_CHECKING:
    from table_service.app.models.data import TableRow

from table_service.app.core import Base


class DataTable(Base):
    __tablename__ = "data_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    columns_schema: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)

    created_by_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    permissions: Mapped[List["TablePermission"]] = relationship(
        "TablePermission", back_populates="table", cascade="all, delete-orphan"
    )
    rows: Mapped[List["TableRow"]] = relationship(
        "TableRow", back_populates="table", cascade="all, delete-orphan"
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

    table: Mapped["DataTable"] = relationship("DataTable", back_populates="permissions")
