from sqlalchemy import select, update, delete, insert, asc, desc
from typing import Any, Optional, List

from backend.app.models import TableRow, DataTable
from backend.app.repository.base import Base
from backend.app.schemas import TableRowCreate, TableRowUpdate


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
        async with self._session_scope() as session:
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

            return (await session.scalars(stmt)).all()

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

        async with self._session_scope() as session:
            stmt = (
                insert(TableRow)
                .values(table_id=table_id, row_data=row_data_dict)
                .returning(TableRow)
            )
            return (await session.scalars(stmt)).one_or_none()

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

        async with self._session_scope() as session:
            values_to_insert = [
                {
                    "table_id": table_id,
                    "row_data": (
                        row.row_data if hasattr(row, "row_data") else row.model_dump()
                    ),
                }
                for row in rows_data
            ]

            stmt = insert(TableRow).values(values_to_insert)
            result = await session.execute(stmt)
            return result.rowcount

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
        async with self._session_scope() as session:
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

            return (await session.scalars(stmt)).one_or_none()

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

        async with self._session_scope() as session:
            stmt = delete(TableRow).where(
                TableRow.table_id == table_id, TableRow.id == row_id
            )

            result = await session.execute(stmt)
            return result.rowcount > 1

    #
    # async def delete_task(self, task_id: UUID, user_id: UUID) -> None:
    #     """Retrieve all tasks from the database.
    #
    #     Returns:
    #         list[Task]: List of all tasks
    #     """
    #     async with self._session_scope() as session:
    #         stmt = delete(Task).where(Task.task_id == task_id, Task.user_id == user_id)
    #         await session.execute(stmt)
    #
