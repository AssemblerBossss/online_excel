from typing import Optional, Literal, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas import TableRowResponse


class DataService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.data_repo = DataRepository(db)
        self.table_repo = TableRepository(db)

    async def get_table_rows(
        self,
        table_id: str,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Literal["asc", "desc"] = "asc"
    ) -> List[TableRowResponse]:
        """Получить строки таблицы"""

        # table = await self.table_repo.get_table_with_access(table_id, user_id)
        # if not table:
        #     raise AccessDeniedException("No access to this table")
        #
        # rows = await self.data_repo.get_rows_by_table_id(
        #     table_id, skip, limit, sort_by, sort_order
        # )
        #
        # return [TableRowResponse(
        #     "id"=row.id,
        #     "table_id"=row.table_id,
        #     "row_data"=row.row_data)
        # for row in rows]

        pass

    async def create_table_row(
            self,
            table_id: int,
            user_id: int,
            row_data: Dict[str, Any]
    ) -> TableRowResponse:
        """Создать новую строку в таблице"""
        # Проверяем доступ на запись
        table = await self.table_repo.get_table_with_write_access(table_id, user_id)
        if not table:
            raise AccessDeniedException("No write access to this table")

        # Валидация данных по схеме таблицы
        validation_errors = self._validate_row_data_with_schema(table.columns_schema, row_data)
        if validation_errors:
            raise ValidationException("; ".join(validation_errors))

        # Создаем строку
        row = await self.data_repo.create_row(table_id, row_data)

        logger.info(f"User {user_id} created row {row.id} in table {table_id}")
        return {
            "id": row.id,
            "table_id": row.table_id,
            "row_data": row.row_data,
            "created_at": row.created_at
        }

    async def update_table_row(
            self,
            table_id: int,
            row_id: int,
            user_id: int,
            row_data: Dict[str, Any]
    ) -> Optional[TableRowResponse]:
        """Обновить строку таблицы"""
        # Проверяем доступ на запись
        table = await self.table_repo.get_table_with_write_access(table_id, user_id)
        if not table:
            raise AccessDeniedException("No write access to this table")

        # Валидация данных
        validation_errors = self._validate_row_data_with_schema(table.columns_schema, row_data)
        if validation_errors:
            raise ValidationException("; ".join(validation_errors))

        # Обновляем строку
        row = await self.data_repo.update_row(table_id, row_id, row_data)
        if not row:
            raise NotFoundException("Row not found")

        logger.info(f"User {user_id} updated row {row_id} in table {table_id}")
        return {
            "id": row.id,
            "table_id": row.table_id,
            "row_data": row.row_data,
            "updated_at": row.updated_at
        }

    async def delete_table_row(
            self,
            table_id: int,
            row_id: int,
            user_id: int
    ) -> bool:
        """Удалить строку таблицы"""
        # Проверяем доступ на запись
        table = await self.table_repo.get_table_with_write_access(table_id, user_id)
        if not table:
            raise AccessDeniedException("No write access to this table")

        # Удаляем строку
        success = await self.data_repo.delete_row(table_id, row_id)
        if not success:
            raise NotFoundException("Row not found")

        logger.info(f"User {user_id} deleted row {row_id} from table {table_id}")
        return True




