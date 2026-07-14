import logging

from fastapi import UploadFile
import pandas as pd
from pydantic import ValidationError

from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.schemas import (
    DataTableResponse,
    DataTableCreate,
    DataTableUpdate,
)
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
        permission_service: PermissionService,
        search_service: SearchService | None = None,
        excel_processor: ExcelProcessorService | None = None,
    ):
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

    async def get_all_tables(self, uow_session: UnitOfWork) -> list[DataTableResponse]:
        """Получить список всех таблиц"""
        async with uow_session.start():
            tables = await uow_session.tables.get_all_tables()
            return [self._to_response(t) for t in tables] if tables else []

    async def get_trash_tables(
        self, uow_session: UnitOfWork
    ) -> list[DataTableResponse]:
        """Получить список всех таблиц в корзине"""
        async with uow_session.start():
            trashed_tables = await uow_session.tables.get_trash()
            return (
                [self._to_response(t) for t in trashed_tables] if trashed_tables else []
            )

    async def get_table_by_id(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTableResponse:
        """Получить таблицу по ID с проверкой прав на чтение."""
        async with uow_session.start():
            table = await self.permission_service.get_table_with_read_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )
        return self._to_response(table)

    async def create_table(
        self, uow_session: UnitOfWork, table_data: DataTableCreate, user_id: int
    ) -> DataTableResponse:
        """Создать новую таблицу"""
        async with uow_session.start():
            payload = table_data.model_dump()
            table = await uow_session.tables.create_table(
                table_data=payload, user_id=user_id
            )
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
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        update_data: DataTableUpdate,
    ) -> DataTableResponse:
        async with uow_session.start():
            await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            payload = update_data.model_dump(exclude_none=True)
            updated = await uow_session.tables.update_table(table_id, payload)
            if not updated:
                raise CanNotUpdateTableException()

            if self.search_service and payload:
                await self.search_service.update_table(table_id=updated.id, **payload)

            logger.info("User %s updated table %s", user_id, table_id)
            return self._to_response(updated)

    async def duplicate_table(
        self,
        uow_session: UnitOfWork,
        source_table_id: int,
        user_id: int,
        user_role: str,
        with_rows: bool = False,
        new_name: str | None = None,
    ) -> DataTableResponse:
        """
        Клонировать таблицу: копирует columns_schema, опционально строки.

        Клон создаётся приватным (is_public=False) и принадлежит текущему пользователю.
        """
        async with uow_session.start():
            source_table = await self.permission_service.get_table_with_read_access(
                uow_session=uow_session,
                table_id=source_table_id,
                user_id=user_id,
                user_role=user_role,
            )

            new_name = new_name or f"Копия {source_table.name}"

            payload = {
                "name": new_name,
                "description": source_table.description,
                "is_public": False,
                "columns_schema": source_table.columns_schema,
            }

            new_table = await uow_session.tables.create_table(
                table_data=payload, user_id=user_id
            )
            if not new_table:
                raise CanNotCreateTableException()

            copied = 0
            if with_rows:
                copied = await uow_session.data.copy_rows(
                    source_table_id=source_table.id, target_table_id=new_table.id
                )

            if self.search_service:
                await self.search_service.index_table(
                    table_id=new_table.id,
                    name=new_table.name,
                    description=new_table.description,
                    is_public=new_table.is_public,
                    created_by_id=new_table.created_by_id,
                )

            logger.info(
                "User %s duplicated table %s -> %s (with_rows=%s, rows copied=%s)",
                user_id,
                source_table.id,
                new_table.id,
                with_rows,
                copied,
            )
            return self._to_response(new_table)

    async def create_table_from_excel_file(
        self,
        uow_session: UnitOfWork,
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
            async with uow_session.start():
                table_data = DataTableCreate(
                    name=table_name,
                    description=description,
                    is_public=False,
                    columns_schema=columns_schema,
                )

                payload = table_data.model_dump()
                table = await uow_session.tables.create_table(
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

                rows, failed = self.excel_processor.build_rows(df)
                created = await uow_session.data.bulk_create_table_row(
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

    async def delete_table(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> None:
        """Удалить таблицу."""
        async with uow_session.start():
            table = await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            if not await uow_session.tables.soft_delete_table(table_id=table_id):
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

    async def permanent_delete_table(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> None:
        """Удалить таблицу."""
        async with uow_session.start():
            table = await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            if not await uow_session.tables.delete_table(table_id=table_id):
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

    async def restore_table(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> None:
        """Восстановить таблицу из корзины."""
        async with uow_session.start():
            await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            restored = await uow_session.tables.restore_table(table_id=table_id)
            if not restored:
                raise NotFoundException("Table not found in trash")

            if self.search_service:
                await self.search_service.index_table(
                    table_id=restored.id,
                    name=restored.name,
                    description=restored.description,
                    is_public=restored.is_public,
                    created_by_id=restored.created_by_id,
                )

            logger.info("User %s restored table %s from trash", user_id, table_id)
