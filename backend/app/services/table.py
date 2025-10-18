from backend.app.schemas import DataTableResponse, DataTableCreate
from backend.app.repository import TableRepository


class TableService:

    def __init__(self):
        self.table_repo = TableRepository()

    async def create_table(
        self, table_data: DataTableCreate, user_id: int
    ) -> DataTableResponse:
        """
        Создать новую таблицу

        Args:
            table_data: Данные для создания таблицы
            user_id: ID пользователя-создателя

        Returns:
            DataTableResponse: Созданная таблица
        """

        table = await self.table_repo.create_table(table_data, user_id)

        if not table:
            raise Exception("Не удалось создать таблицу")

        return DataTableResponse(
            id=table.id,
            name=table.name,
            description=table.description,
            is_public=table.is_public,
            columns_schema=table.columns_schema,
            created_by=table.created_by,
            created_at=table.created_at,
            updated_at=table.updated_at,
        )

