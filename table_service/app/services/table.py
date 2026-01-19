from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
import pandas as pd

from table_service.app.schemas import DataTableResponse, DataTableCreate
from table_service.app.repository import TableRepository, DataRepository
from table_service.app.models import DataTable
from table_service.app.services.excel_processor import (
    _generate_columns_schema_from_dataframe,
    _import_excel_data_to_table,
)


ALLOWED_EXCEL_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "application/wps-office.xlsx",
}


class TableService:

    def __init__(
        self, table_repository: TableRepository, data_repository: DataRepository
    ):
        self.table_repo = table_repository
        self.data_repo = data_repository

    def _to_response(self, table) -> DataTableResponse:
        return DataTableResponse(
            id=table.id,
            name=table.name,
            description=table.description,
            is_public=table.is_public,
            columns_schema=table.columns_schema,
            created_by=table.created_by_id,
            created_at=table.created_at,
            updated_at=table.updated_at,
        )

    async def get_all_tables(self) -> List[DataTableResponse]:
        """
        Получить список всех таблиц
        Returns:
            List[DataTableResponse]: Список таблиц
        """
        tables = await self.table_repo.get_all_tables()
        if not tables:
            return []
        return [self._to_response(table) for table in tables]

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

        return self._to_response(table)

    async def create_table_from_excel_file(
        self,
        excel_file: UploadFile,
        user_id: int,
        table_name: str = None,
        description: str = None,
    ) -> DataTableResponse:
        """
        Создать новую таблицу из Excel файла

        Args:
            excel_file: Excel файл для создания таблицы
            user_id: ID пользователя-создателя
            table_name: Название таблицы (если None - используется имя файла)
            description: Описание таблицы

        Returns:
            DataTableResponse: Созданная таблица

        """
        # Валидация файла
        if not excel_file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(
                400, "Файл должен быть в формате Excel (.xlsx или .xls)"
            )

        if excel_file.content_type not in ALLOWED_EXCEL_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: '{excel_file.content_type}'. Only {', '.join(ALLOWED_EXCEL_MIME_TYPES)} are allowed.",
            )

        try:
            df = pd.read_excel(excel_file.file)

            # Если название таблицы не указано, используем имя файла без расширения
            if table_name is None:
                table_name = excel_file.filename.rsplit(".", 1)[0]

            # Генерация схемы колонок на основе DataFrame
            columns_schema = _generate_columns_schema_from_dataframe(df)

            if not description:
                description = f"Таблица создана из файла {excel_file.filename}"

            table_data = DataTableCreate(
                name=table_name,
                description=description,
                is_public=False,
                columns_schema=columns_schema,
            )

            table = await self.table_repo.create_table(table_data, user_id)

            if not table:
                raise Exception("Не удалось создать таблицу из Excel файла")

            await _import_excel_data_to_table(self.data_repo, table.id, df)

            return self._to_response(table)

        except pd.errors.EmptyDataError:
            raise HTTPException(400, "Excel файл пустой")
        except pd.errors.ParserError:
            raise HTTPException(400, "Ошибка парсинга Excel файла")
        except Exception as e:
            raise HTTPException(500, f"Ошибка обработки Excel файла: {str(e)}")

    async def delete_table(self, table_id: int, user_id: int) -> bool:
        """
        Удалить таблицу.

        Args:
            table_id: ID таблицы для удаления
            user_id: ID пользователя

        Raises:
            HTTPException 404: Если таблица не найдена или нет доступа
            HTTPException 500: Если не удалось удалить таблицу
        """
        table: Optional[DataTable] = await self.table_repo.get_table_with_write_access(
            table_id, user_id
        )

        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table not found or access denied",
            )

        deleted = await self.table_repo.delete_table(table_id=table_id, user_id=user_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete table",
            )
        # logger.info(f"User {user_id} deleted table {table_id} (name: {table.name})")

        return None
