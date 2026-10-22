from typing import Any

from sqlalchemy import Index, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from table_service.app.core import Base


class SheetCell(Base):
    """Одна непустая ячейка листа. Пустые ячейки в БД не хранятся."""

    __tablename__ = "sheet_cells"
    __table_args__ = (Index("ix_sheet_cells_table_col", "table_id", "col"),)

    table_id: Mapped[int] = mapped_column(
        ForeignKey("data_tables.id", ondelete="CASCADE"), primary_key=True
    )

    # Сдвиг колонок (вставка/удаление) ищет ячейки по (table_id, col)
    row: Mapped[int] = mapped_column(Integer, primary_key=True)
    col: Mapped[int] = mapped_column(Integer, primary_key=True)

    raw: Mapped[str | None] = mapped_column(Text)
    # Вычисленное значение: число, строка, bool или {"e": "#DIV/0!"} для ошибки.
    value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # Оформление: {"bg": "#ffeb3b", "bold": true, ...}. NULL — без оформления.
    style: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))

    def __repr__(self):
        return f"<SheetCell(table={self.table_id}, r={self.row}, c={self.col})>"
