from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional, Dict, Any, List

from backend.app.core.database import Base


class TableRow(Base):
    __tablename__ = "table_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("data_tables.id"), nullable=False)

    # Динамические данные
    row_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Мета-информация
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    table: Mapped["DataTable"] = relationship("DataTable", back_populates="rows")

    # Индексы
    __table_args__ = (
        Index('ix_table_rows_table_id_created', 'table_id', 'created_at'),
        Index('ix_table_rows_table_id_updated', 'table_id', 'updated_at'),
    )

    def __repr__(self):
        return f"<TableRow(id={self.id}, table_id={self.table_id})>"