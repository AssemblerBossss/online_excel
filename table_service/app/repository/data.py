from collections.abc import AsyncIterator

from sqlalchemy import (
    ColumnElement,
    Numeric,
    Sequence,
    String,
    asc,
    cast,
    delete,
    desc,
    func,
    insert,
    literal,
    select,
    update,
)

from table_service.app.models import TableRow
from table_service.app.repository.base import Base
from table_service.app.schemas import (
    FilterOperator,
    RowFilter,
    TableRowCreate,
    TableRowUpdate,
)


class DataRepository(Base):
    # Реальные колонки таблицы (всё остальное живёт в JSON-поле row_data)
    _REAL_COLUMNS = frozenset({"id", "created_at", "updated_at"})

    @classmethod
    def _text_expr(cls, field: str) -> ColumnElement[str]:
        """Текстовое выражение колонки (для contains / текстового сравнения)."""
        if field in cls._REAL_COLUMNS:
            return cast(getattr(TableRow, field), String)
        return TableRow.row_data[field].as_string()

    @classmethod
    def _sortable_expr(cls, field: str, numeric: bool) -> ColumnElement[str]:
        """Выражение для ORDER BY / сравнения. Числовые колонки кастуются в Numeric."""
        if field in cls._REAL_COLUMNS:
            return getattr(TableRow, field)
        text = TableRow.row_data[field].as_string()
        if numeric:
            return cast(func.nullif(text, ""), Numeric)
        return text

    @classmethod
    def _build_conditions(
        cls,
        table_id: int,
        filters: list[RowFilter],
        numeric_fields: set[str],
    ) -> list:
        """Собрать список условий WHERE из фильтров (значения параметризуются)."""
        conditions = [TableRow.table_id == table_id]

        for f in filters:
            numeric = f.field in numeric_fields

            if f.op is FilterOperator.contains:
                conditions.append(cls._text_expr(f.field).ilike(f"%{f.value}%"))
                continue

            if f.op in (FilterOperator.eq, FilterOperator.ne):
                col = (
                    cls._sortable_expr(f.field, numeric)
                    if numeric
                    else cls._text_expr(f.field)
                )
                val = cls._to_number(f.value) if numeric else f.value
                conditions.append(
                    col == val if f.op is FilterOperator.eq else col != val
                )
                continue

            # gt / gte / lt / lte
            col = cls._sortable_expr(f.field, numeric)
            val = cls._to_number(f.value) if numeric else f.value
            ops = {
                FilterOperator.gt: col > val,
                FilterOperator.gte: col >= val,
                FilterOperator.lt: col < val,
                FilterOperator.lte: col <= val,
            }
            conditions.append(ops[f.op])

        return conditions

    async def stream_rows_by_table_id(
        self, table_id: int, chunk_size: int = 2000
    ) -> AsyncIterator[TableRow | None]:
        """
        Потоково читает строки таблицы чанками, возвращая по одной строке через асинхронный генератор.
        """
        stmt = (
            select(TableRow)
            .where(TableRow.table_id == table_id)
            .execution_options(yield_per=chunk_size)
        )

        result = await self._session.stream(stmt)
        async for row in result.scalars():
            yield row

    async def get_rows_by_table_id(
        self,
        table_id: int,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str | None = "asc",
        filters: list[RowFilter] | None = None,
        numeric_fields: set[str] | None = None,
    ) -> Sequence[TableRow]:
        """Получить строки таблицы с фильтрацией, сортировкой и пагинацией."""
        filters = filters or []
        numeric_fields = numeric_fields or set()
        sort_by = sort_by or "id"

        conditions = self._build_conditions(
            table_id=table_id, filters=filters, numeric_fields=numeric_fields
        )
        sort_expr = self._sortable_expr(sort_by, sort_by in numeric_fields)
        direction = asc if (sort_order or "asc").lower() == "asc" else desc
        stmt = (
            select(TableRow)
            .where(*conditions)
            .order_by(direction(sort_expr), asc(TableRow.id))
            .limit(limit)
            .offset(skip)
        )

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_rows_by_table_id(
        self,
        table_id: int,
        filters: list[RowFilter] | None = None,
        numeric_fields: set[str] | None = None,
    ) -> int:
        """Посчитать строки таблицы с учётом тех же фильтров (без limit/offset)."""
        conditions = self._build_conditions(
            table_id=table_id,
            filters=filters or [],
            numeric_fields=numeric_fields or set(),
        )

        stmt = select(func.count()).select_from(TableRow).where(*conditions)
        result = await self._session.execute(stmt)
        return result.scalar()

    async def get_row_by_id(self, table_id: int, row_id: int) -> TableRow | None:
        """Получить строку по ID."""
        stmt = select(TableRow).where(
            TableRow.id == row_id,
            TableRow.table_id == table_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_table_row(
        self, table_id: int, row_data: TableRowCreate
    ) -> TableRow | None:
        """
        Создать новую строку в указанной таблице.

        Args:
            table_id: ID таблицы, в которую добавляется строка
            row_data: Данные строки в формате JSON/dict. Должны соответствовать схеме таблицы.
        """
        row_data_dict = (
            row_data.row_data
            if hasattr(row_data, "row_data")
            else row_data.model_dump()
        )

        new_row = TableRow(table_id=table_id, row_data=row_data_dict)
        self._session.add(new_row)
        await self._session.flush()
        await self._session.refresh(new_row)
        return new_row

    async def bulk_create_table_row(
        self, table_id: int, rows_data: list[TableRowCreate]
    ) -> int:
        """
        Массовое создание строк в таблице.

        Args:
            table_id: ID таблицы, в которую добавляются строки
            rows_data: Список данных строк для вставки
        """
        if not rows_data:
            return 0

        rows_to_insert = []
        for row in rows_data:
            row_data_dict = (
                row.row_data if hasattr(row, "row_data") else row.model_dump()
            )
            rows_to_insert.append(TableRow(table_id=table_id, row_data=row_data_dict))

        self._session.add_all(rows_to_insert)
        await self._session.flush()
        return len(rows_to_insert)

    async def copy_rows(self, source_table_id: int, target_table_id: int) -> int:
        """Скопировать все строки из одной таблицы в другую."""
        select_stmt = select(literal(target_table_id), TableRow.row_data).where(
            TableRow.table_id == source_table_id
        )
        stmt = insert(TableRow).from_select(["table_id", "row_data"], select_stmt)
        result = await self._session.execute(stmt)
        return result.rowcount

    async def update_table_row(
        self,
        table_id: int,
        row_id: int,
        row_data: TableRowUpdate,
    ) -> TableRow | None:
        """
        Обновить строку в указанной таблице.

        Args:
            table_id: ID таблицы, в которую добавляется строка
            row_id: ID строки
            row_data: Данные строки в формате JSON/dict. Должны соответствовать схеме таблицы.
        """
        row_data_dict = (
            row_data.row_data
            if hasattr(row_data, "row_data")
            else row_data.model_dump()
        )

        stmt = (
            update(TableRow)
            .where(TableRow.table_id == table_id, TableRow.id == row_id)
            .values(row_data=row_data_dict)
            .returning(TableRow)
        )

        return (await self._session.scalars(stmt)).one_or_none()

    async def delete_table_row(
        self,
        table_id: int,
        row_id: int,
    ) -> bool:
        """
        Удалить строку из таблицы.
        Returns:
            bool: True если строка была удалена, False если не найдена
        """

        stmt = delete(TableRow).where(
            TableRow.table_id == table_id, TableRow.id == row_id
        )

        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def get_all_rows_by_table_id(self, table_id: int) -> Sequence[TableRow]:
        """Получить все строки таблицы, отсортированные по id (для экспорта)"""
        stmt = (
            select(TableRow)
            .where(TableRow.table_id == table_id)
            .order_by(asc(TableRow.id))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def bulk_delete_table_rows(
        self, table_id: int, row_ids: list[int]
    ) -> Sequence[int]:
        """
        Удалить несколько строк одним запросом.
        Возвращает ID реально удалённых строк (может быть меньше запрошенных —
        часть могла уже не существовать).
        """
        stmt = (
            delete(TableRow)
            .where(TableRow.table_id == table_id, TableRow.id.in_(row_ids))
            .returning(TableRow.id)
        )

        result = await self._session.execute(stmt)
        return result.scalars().all()
