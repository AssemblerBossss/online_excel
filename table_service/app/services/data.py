import logging
from typing import Literal

from table_service.app.schemas import TableRowResponse, TableRowCreate, TableRowUpdate
from table_service.app.repository import DataRepository, TableRepository
from table_service.app.exceptions import (
    AccessDeniedException,
    ValidationException,
    NotFoundException,
)
from table_service.app.models import TableRow
from table_service.app.services.permission import PermissionService
from table_service.app.services.data_validation import DataValidationService


logger = logging.getLogger(__name__)


class DataService:
    def __init__(
        self,
        data_repo: DataRepository,
        table_repo: TableRepository,
        permission_service: PermissionService,
        validation_service: DataValidationService | None = None,
    ):
        self.data_repo = data_repo
        self.table_repo = table_repo
        self.permission_service = permission_service
        self.validation_service = validation_service or DataValidationService()

    @staticmethod
    def _to_row_response(row: TableRow) -> TableRowResponse:
        return TableRowResponse(
            id=row.id,
            table_id=row.table_id,
            row_data=row.row_data,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_table_rows(
        self,
        table_id: int,
        user_id: int,
        user_role: str,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> list[TableRowResponse]:
        """Получить строки таблицы"""

        table = await self.table_repo.get_table_by_id(table_id)
        if not table:
            raise NotFoundException("Таблица не найдена")

        if not await self.permission_service.check_read_access(
            table=table, user_id=user_id, user_role=user_role
        ):
            raise AccessDeniedException()

        if not sort_by:
            sort_by = "id"

        rows = await self.data_repo.get_rows_by_table_id(
            table_id=table_id,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return [self._to_row_response(row) for row in rows]

    async def get_table_row(
        self, table_id: int, user_id: int, user_role: str, row_id: int
    ) -> TableRowResponse | None:
        """Получить строку таблицы"""
        table = await self.table_repo.get_table_by_id(table_id)
        if not table:
            raise NotFoundException("Таблица не найдена")

        if not await self.permission_service.check_read_access(
            table=table, user_id=user_id, user_role=user_role
        ):
            raise AccessDeniedException()

        row = await self.data_repo.get_row_by_id(table_id=table_id, row_id=row_id)
        if not row:
            raise NotFoundException()

        return self._to_row_response(row)

    async def create_table_row(
        self, table_id: int, user_id: int, user_role: str, row_data: TableRowCreate
    ) -> TableRowResponse:
        """Создать новую строку в таблице"""
        table = await self.table_repo.get_table_by_id(table_id)
        if not table:
            raise NotFoundException("Таблица не найдена")

        if not await self.permission_service.check_write_access(
            table=table, user_id=user_id, user_role=user_role
        ):
            raise AccessDeniedException()

        validation_errors = self.validation_service.validate_row_data(
            table_columns_schema=table.columns_schema,
            row_data=row_data,
            raise_on_error=False,
        )
        if validation_errors:
            raise ValidationException("; ".join(validation_errors))

        row = await self.data_repo.create_table_row(
            table_id=table_id, row_data=row_data
        )
        logger.info("User %s created row %s in table %s", user_id, row.id, table_id)

        return self._to_row_response(row)

    async def update_table_row(
        self,
        table_id: int,
        row_id: int,
        user_id: int,
        user_role: str,
        row_data: TableRowUpdate,
    ) -> TableRowResponse | None:
        """Обновить строку таблицы"""
        table = await self.table_repo.get_table_by_id(table_id)
        if not table:
            raise NotFoundException("Таблица не найдена")

        if not await self.permission_service.check_write_access(
            table=table, user_id=user_id, user_role=user_role
        ):
            logger.warning("User %s denied write access to table %s", user_id, table_id)
            raise AccessDeniedException()

        validation_errors = self.validation_service.validate_row_data(
            table_columns_schema=table.columns_schema,
            row_data=row_data,
            raise_on_error=False,
        )
        if validation_errors:
            raise ValidationException("; ".join(validation_errors))

        row = await self.data_repo.update_table_row(
            table_id=table_id, row_id=row_id, row_data=row_data
        )
        if not row:
            raise NotFoundException()

        return self._to_row_response(row)

    async def delete_table_row(
        self, table_id: int, row_id: int, user_id: int, user_role: str
    ) -> None:
        """Удалить строку таблицы"""
        table = await self.table_repo.get_table_by_id(table_id)
        if not table:
            raise NotFoundException("Таблица не найдена")

        if not await self.permission_service.check_write_access(
            table=table, user_id=user_id, user_role=user_role
        ):
            raise AccessDeniedException()

        row = await self.data_repo.get_row_by_id(table_id=table_id, row_id=row_id)
        if not row:
            raise NotFoundException()

        await self.data_repo.delete_table_row(table_id=table_id, row_id=row_id)
        logger.info("User %s deleted row %s from table %s", user_id, row_id, table_id)
