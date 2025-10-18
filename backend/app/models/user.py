from sqlalchemy import String, Integer, Boolean, DateTime, Enum, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional, List
import enum

from backend.app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    table_permissions: Mapped[List["TablePermission"]] = relationship(
        "TablePermission",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    created_tables: Mapped[List["DataTable"]] = relationship(
        "DataTable",
        back_populates="created_by"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"