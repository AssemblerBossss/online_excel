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
