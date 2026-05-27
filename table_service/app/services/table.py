import logging
from fastapi import UploadFile
import pandas as pd
from pydantic import ValidationError

from table_service.app.schemas import (
    DataTableResponse,
    DataTableCreate,
    DataTableUpdate,
)
from table_service.app.repository import TableRepository, DataRepository
from table_service.app.models import DataTable
from table_service.app.services.excel_processor import ExcelProcessorService
from table_service.app.services.search import SearchService
from table_service.app.services.permission import PermissionService
from table_service.app.exceptions import (
    NotFoundException,
    CanNotCreateTableException,
    InvalidFileFormatException,
    InvalidFileMimeTypeException,
    EmptyFileException,
    FileParseException,
    CanNotDeleteTableException,
    CanNotUpdateTableException,
    AccessDeniedException,
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
        self,
        table_repository: TableRepository,
        data_repository: DataRepository,
        permission_service: PermissionService,
        search_service: SearchService | None = None,
        excel_processor: ExcelProcessorService | None = None,
    ):
        self.table_repo = table_repository
        self.data_repo = data_repository
        self.permission_service = permission_service
        self.search_service = search_service
        self.excel_processor = excel_processor or ExcelProcessorService()

    def _to_response(self, table: DataTable) -> DataTableResponse:
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
        table = await self.table_repo.get_table_by_id(table_id)
        if not table:
            logger.warning(
                "Table %s not found or access denied for user %s", table_id, user_id
            )
            raise NotFoundException("Table not found or access denied")
        if not await self.permission_service.check_read_access(
            table=table, user_id=user_id, user_role=user_role
        ):
            raise AccessDeniedException()

        return self._to_response(table)

    async def create_table(
        self, table_data: DataTableCreate, user_id: int
    ) -> DataTableResponse:
        """Создать новую таблицу"""

        payload = table_data.model_dump()
        table = await self.table_repo.create_table(table_data=payload, user_id=user_id)
        if not table:
            raise CanNotCreateTableException()

        if self.search_service:
            await self.search_service.index_table(
                table_id=table.id,
                name=table.name,
                description=table.description,
                is_public=table.is_public,
                created_by_id=table.created_by_id,
            )
        logger.info(
            "User %s created table %s (name: '%s')", user_id, table.id, table.name
        )
        return self._to_response(table)

    async def update_table(
        self, table_id: int, user_id: int, user_role: str, update_data: DataTableUpdate
    ) -> DataTableResponse:

        if not (table := await self.table_repo.get_table_by_id(table_id=table_id)):
            raise NotFoundException("Table not found or access denied")

        if not await self.permission_service.check_write_access(
            table=table, user_id=user_id, user_role=user_role
        ):
            raise AccessDeniedException()

        payload = update_data.model_dump(exclude_none=True)
        updated = await self.table_repo.update_table(table_id, payload)
        if not updated:
            raise CanNotUpdateTableException()

        if self.search_service and payload:
            await self.search_service.update_table(table_id=updated.id, **payload)

        logger.info("User %s updated table %s", user_id, table_id)
        return self._to_response(updated)

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
            logger.warning(
                "User %s uploaded file with invalid format: '%s'",
                user_id,
                excel_file.filename,
            )

            raise InvalidFileFormatException(
                "Файл должен быть в формате Excel (.xlsx или .xls)"
            )

        if excel_file.content_type not in ALLOWED_EXCEL_MIME_TYPES:
            logger.warning(
                "User %s uploaded file with unsupported MIME type: '%s'",
                user_id,
                excel_file.content_type,
            )
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
            columns_schema = self.excel_processor.build_columns_schema(df)

            if not description:
                description = f"Таблица создана из файла {excel_file.filename}"

            table_data = DataTableCreate(
                name=table_name,
                description=description,
                is_public=False,
                columns_schema=columns_schema,
            )

            payload = table_data.model_dump()
            table = await self.table_repo.create_table(
                table_data=payload, user_id=user_id
            )

            if not table:
                logger.error(
                    "Failed to create table from Excel '%s' for user %s",
                    excel_file.filename,
                    user_id,
                )
                raise CanNotCreateTableException()

            if self.search_service:
                await self.search_service.index_table(
                    table_id=table.id,
                    name=table.name,
                    description=table.description,
                    is_public=table.is_public,
                    created_by_id=table.created_by_id,
                )
                logger.info(
                    "Table %s indexed in Elasticsearch from Excel import", table.id
                )

            rows, failed = self.excel_processor.build_rows(df)
            created = await self.data_repo.bulk_create_table_row(
                table_id=table.id, rows_data=rows
            )
            logger.info(
                "User %s created table %s from Excel '%s' "
                "(%s columns, %s rows: %s imported, %s failed)",
                user_id,
                table.id,
                excel_file.filename,
                len(df.columns),
                len(df),
                created,
                failed,
            )
            return self._to_response(table)

        except pd.errors.EmptyDataError:
            logger.warning(
                "User %s uploaded empty Excel file '%s'", user_id, excel_file.filename
            )
            raise EmptyFileException("Excel файл пустой")
        except ValidationError:
            raise
        except (pd.errors.ParserError, ValueError, TypeError):
            logger.warning(
                "User %s uploaded unparseable Excel file '%s'",
                user_id,
                excel_file.filename,
            )
            raise FileParseException("Ошибка парсинга Excel файла")

    async def delete_table(self, table_id: int, user_id: int, user_role: str) -> None:
        """Удалить таблицу."""
        table: DataTable | None = await self.table_repo.get_table_by_id(table_id)
        if not table:
            raise NotFoundException("Table not found")

        if not await self.permission_service.check_write_access(
            table=table, user_id=user_id, user_role=user_role
        ):
            raise AccessDeniedException()

        if not await self.table_repo.delete_table(table_id=table_id):
            raise CanNotDeleteTableException()

        if self.search_service:
            try:
                await self.search_service.delete_from_index(table_id=table_id)
            except Exception:
                logger.warning(
                    "Failed to delete table %s from search index, "
                    "data may be orphaned until next sync",
                    table_id,
                )

        logger.info(
            "User %s deleted table %s (name: %s)", user_id, table_id, table.name
        )
