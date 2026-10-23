from collections.abc import AsyncIterator, Sequence
from typing import Any, Literal

from sqlalchemy import Row, delete, insert, literal, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from table_service.app.models import SheetCell
from table_service.app.repository.base import Base

# asyncpg принимает не больше 32767 параметров на запрос: 5 колонок * 5000 строк = 25000
UPSERT_CHUNK = 5000


class CellRepository(Base):
    """Репозиторий ячеек листа"""

    @staticmethod
    def _axis_column(axis: Literal["row", "col"]):
        return SheetCell.row if axis == "row" else SheetCell.col

    async def get_all(self, table_id: int) -> Sequence[Row]:
        stmt = (
            select(
                SheetCell.row,
                SheetCell.col,
                SheetCell.raw,
                SheetCell.value,
                SheetCell.style,
            )
            .where(SheetCell.table_id == table_id)
            .order_by(SheetCell.row, SheetCell.col)
        )

        return (await self._session.execute(stmt)).all()

    async def stream_all(
        self, table_id: int, chunk_size: int = 5000
    ) -> AsyncIterator[Row]:
        """Потоково отдаёт ячейки в порядке строка -> колонка (для экспорта)."""
        stmt = (
            select(
                SheetCell.row,
                SheetCell.col,
                SheetCell.raw,
                SheetCell.value,
                SheetCell.style,
            )
            .where(SheetCell.table_id == table_id)
            .order_by(SheetCell.row, SheetCell.col)
            .execution_options(yield_per=chunk_size)
        )

        result = await self._session.stream(stmt)
        async for cell in result:
            yield cell

    async def upsert_cells(self, table_id: int, cells: list[dict[str, Any]]) -> None:
        """Записать raw+value. cells: [{row, col, raw, value}], без дублей (row, col)."""
        for start in range(0, len(cells), UPSERT_CHUNK):
            chunk = cells[start : start + UPSERT_CHUNK]
            stmt = pg_insert(SheetCell).values(
                [{"table_id": table_id, **cell} for cell in chunk]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[SheetCell.table_id, SheetCell.row, SheetCell.col],
                set_={"raw": stmt.excluded.raw, "value": stmt.excluded.value},
            )
            await self._session.execute(stmt)

    async def upsert_styles(self, table_id: int, styles: list[dict[str, Any]]) -> None:
        """Записать style. styles: [{row, col, style}], без дублей (row, col)."""
        for start in range(0, len(styles), UPSERT_CHUNK):
            chunk = styles[start : start + UPSERT_CHUNK]
            stmt = pg_insert(SheetCell).values(
                [{"table_id": table_id, **item} for item in chunk]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[SheetCell.table_id, SheetCell.row, SheetCell.col],
                set_={"style": stmt.excluded.style},
            )
            await self._session.execute(stmt)

    async def delete_empty(self, table_id: int, min_row: int, max_row: int) -> None:
        """Убрать «пустые» ячейки (нет ни raw, ни value, ни style) в диапазоне строк."""
        stmt = delete(SheetCell).where(
            SheetCell.table_id == table_id,
            SheetCell.row.between(min_row, max_row),
            SheetCell.raw.is_(None),
            SheetCell.value.is_(None),
            SheetCell.style.is_(None),
        )
        await self._session.execute(stmt)

    async def delete_range(
        self, table_id, axis: Literal["row", "col"], start: int, count: int
    ) -> None:
        """Удалить все ячейки в строках (или колонках) [start, start + count)."""
        column = self._axis_column(axis)
        stmt = delete(SheetCell).where(
            SheetCell.table_id == table_id,
            column >= start,
            column <= start + count,
        )
        await self._session.execute(stmt)

    async def bulk_insert(self, table_id: int, cells: list[dict[str, Any]]) -> None:
        """Вставка новых ячеек. cells: [{row, col, raw, value, style}]."""
        for start in range(0, len(cells), UPSERT_CHUNK // 2):
            chunk = cells[start : start + UPSERT_CHUNK // 2]
            await self._session.execute(
                insert(SheetCell), [{"table_id": table_id, **cell} for cell in chunk]
            )
        return len(cells)

    async def shift(
        self, table_id: int, axis: Literal["row", "col"], from_index: int, delta: int
    ) -> None:
        """Сдвинуть все ячейки с индексом >= from_index на delta (может быть < 0).

        Делается в два шага через отрицательные индексы, чтобы не нарушать PRIMARY KEY
        посреди UPDATE: PK в PostgreSQL проверяется построчно, а не по завершении запроса.
        """
        column = self._axis_column(axis)
        name = axis
        await self._session.execute(
            update(SheetCell)
            .where(SheetCell.table_id == table_id, column >= from_index)
            .values({name: -(column + delta) - 1})
        )
        await self._session.execute(
            update(SheetCell)
            .where(SheetCell.table_id == table_id, column < 0)
            .values({name: -column - 1})
        )

    async def copy_cells(self, source_table_id: int, target_table_id: int) -> int:
        """Скопировать все ячейки из одной таблицы в другую."""
        select_stmt = select(
            literal(target_table_id),
            SheetCell.row,
            SheetCell.col,
            SheetCell.raw,
            SheetCell.value,
            SheetCell.style,
        ).where(
            SheetCell.table_id == source_table_id,
        )

        stmt = insert(SheetCell).from_select(
            ["table_id", "row", "col", "raw", "value", "style"], select=select_stmt
        )
        result = await self._session.execute(stmt)
        return result.rowcount
