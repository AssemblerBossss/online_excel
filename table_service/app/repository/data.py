from sqlalchemy import select, update, delete, insert, asc, desc
from typing import Optional, List

from table_service.app.models import TableRow, DataTable
from table_service.app.repository.base import Base
from table_service.app.schemas import TableRowCreate, TableRowUpdate


class DataRepository(Base):

    async def get_rows_by_table_id(
        self,
        table_id: int,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "asc",
    ) -> List[TableRow]:
        """
        Получить строки таблицы с пагинацией и сортировкой.

        Args:
            table_id: ID таблицы для получения строк
            skip: Пагинация
            limit: Максимальное количество возвращаемых строк
            sort_by: Название поля для сортировки. Если None, порядок не гарантируется.
            sort_order: Порядок сортировки - "asc" (по возрастанию) или "desc" (по убыванию)

        Returns:
            List[TableRow]: Список строк таблицы

        Raises:
            SQLAlchemyError: При ошибках выполнения запроса к базе данных
        """

        if sort_order.lower() == "asc":
            stmt = (
                select(TableRow)
                .where(TableRow.table_id == table_id)
                .limit(limit)
                .offset(skip)
                .order_by(asc(sort_by))
            )
        else:
            stmt = (
                select(TableRow)
                .where(TableRow.table_id == table_id)
                .limit(limit)
                .offset(skip)
                .order_by(desc(sort_by))
            )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_table_row(
        self, table_id: int, row_data: TableRowCreate
    ) -> Optional[TableRow]:
        """
        Создать новую строку в указанной таблице.

        Args:
            table_id: ID таблицы, в которую добавляется строка
            row_data: Данные строки в формате JSON/dict. Должны соответствовать схеме таблицы.

        Returns:
            Optional[TableRow]: Созданная строка таблицы или None при ошибке
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
        self, table_id: int, rows_data: List[TableRowCreate]
    ) -> int:
        """
        Массовое создание строк в таблице.

        Args:
            table_id: ID таблицы, в которую добавляются строки
            rows_data: Список данных строк для вставки

        Returns:
            int: Количество созданных строк
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

    async def update_table_row(
        self,
        table_id: int,
        row_id: int,
        row_data: TableRowUpdate,
    ) -> Optional[TableRow]:
        """
        Обновить строку в указанной таблице.

        Args:
            table_id: ID таблицы, в которую добавляется строка
            row_id: ID строки
            row_data: Данные строки в формате JSON/dict. Должны соответствовать схеме таблицы.

        Returns:
            Optional[TableRow]: Обновленная строка таблицы или None при ошибке
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

        Args:
            table_id: ID таблицы
            row_id: ID строки для удаления

        Returns:
            bool: True если строка была удалена, False если не найдена
        """

        stmt = delete(TableRow).where(
            TableRow.table_id == table_id, TableRow.id == row_id
        )

        result = await self._session.execute(stmt)
        return result.rowcount > 0
