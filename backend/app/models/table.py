from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional, List, Dict, Any

from backend.app.core import Base


class DataTable(Base):
    __tablename__ = "data_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    columns_schema: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    created_by: Mapped["User"] = relationship("User", back_populates="created_tables")
    permissions: Mapped[List["TablePermission"]] = relationship(
        "TablePermission",
        back_populates="table",
        cascade="all, delete-orphan"
    )
    rows: Mapped[List["TableRow"]] = relationship(
        "TableRow",
        back_populates="table",
        cascade="all, delete-orphan"
    )



class TablePermission(Base):
    __tablename__ = "table_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    table_id: Mapped[int] = mapped_column(ForeignKey("data_tables.id"), nullable=False)

    can_read: Mapped[bool] = mapped_column(Boolean, default=False)
    can_write: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="table_permissions")
    table: Mapped["DataTable"] = relationship("DataTable", back_populates="permissions")
