import logging
from fastapi import UploadFile
import pandas as pd

from table_service.app.schemas import DataTableResponse, DataTableCreate
from table_service.app.repository import TableRepository, DataRepository
from table_service.app.models import DataTable
from table_service.app.services.excel_processor import (
    _generate_columns_schema_from_dataframe,
    _import_excel_data_to_table,
)

from table_service.app.exceptions import (
    NotFoundException,
    CanNotCreateTableException,
    InvalidFileFormatException,
    InvalidFileMimeTypeException,
    EmptyFileException,
    FileParseException,
    CanNotDeleteTableException,
)

logger = logging.getLogger(__name__)

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

    async def get_all_tables(self) -> list[DataTableResponse]:
        """
        Получить список всех таблиц
        Returns:
            list[DataTableResponse]: Список таблиц
        """
        tables = await self.table_repo.get_all_tables()
        if not tables:
            return []
        return [self._to_response(table) for table in tables]

    async def get_table_by_id(
        self, table_id: int, user_id: int, user_role: str
    ) -> DataTableResponse:
        """Получить таблицу по ID с проверкой прав на чтение."""
        table = await self.table_repo.get_table_with_read_access(
            table_id=table_id, user_id=user_id, user_role=user_role
        )
        if not table:
            raise NotFoundException("Table not found or access denied")
        return self._to_response(table)

    async def create_table(
        self, table_data: DataTableCreate, user_id: int
    ) -> DataTableResponse:
        """Создать новую таблицу"""

        table = await self.table_repo.create_table(table_data, user_id)
        if not table:
            raise CanNotCreateTableException()
        return self._to_response(table)

    async def create_table_from_excel_file(
        self,
        excel_file: UploadFile,
        user_id: int,
        table_name: str | None = None,
        description: str | None = None,
    ) -> DataTableResponse:
        """
        Создать новую таблицу из Excel файла

        Args:
            excel_file: Excel файл для создания таблицы
            user_id: ID пользователя-создателя
            table_name: Название таблицы (если None - используется имя файла)
            description: Описание таблицы
        """
        # Валидация файла
        if not excel_file.filename.endswith((".xlsx", ".xls")):
            raise InvalidFileFormatException(
                "Файл должен быть в формате Excel (.xlsx или .xls)"
            )

        if excel_file.content_type not in ALLOWED_EXCEL_MIME_TYPES:
            raise InvalidFileMimeTypeException(
                f"Unsupported file type: '{excel_file.content_type}'. "
                f"Only {', '.join(ALLOWED_EXCEL_MIME_TYPES)} are allowed."
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
                raise CanNotCreateTableException()

            await _import_excel_data_to_table(self.data_repo, table.id, df)
            return self._to_response(table)

        except pd.errors.EmptyDataError:
            raise EmptyFileException("Excel файл пустой")
        except pd.errors.ParserError:
            raise FileParseException("Ошибка парсинга Excel файла")

    async def delete_table(self, table_id: int, user_id: int, user_role: str) -> None:
        """Удалить таблицу."""
        table: DataTable | None = await self.table_repo.get_table_with_write_access(
            table_id, user_id, user_role=user_role
        )

        if not table:
            raise NotFoundException("Table not found or access denied")

        deleted = await self.table_repo.delete_table(
            table_id=table_id, user_id=user_id, user_role=user_role
        )

        if not deleted:
            raise CanNotDeleteTableException()
        logger.info(
            "User %s deleted table %s (name: %s)", user_id, table_id, table.name
        )
