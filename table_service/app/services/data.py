import logging
from typing import Literal


from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.schemas import (
    TableRowResponse,
    TableRowCreate,
    TableRowUpdate,
    RowFilter,
    COMPARISON_OPERATORS,
    PaginatedRows,
)
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
        permission_service: PermissionService,
        validation_service: DataValidationService | None = None,
    ):

        self.permission_service = permission_service
        self.validation_service = validation_service or DataValidationService()

    @staticmethod
    def _to_row_response(row: TableRow) -> TableRowResponse:
        return TableRowResponse(
            id=row.id,
            table_id=row.table_id,
            row_data=row.row_data,
            formulas=row.formulas,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_table_rows(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        filters: list[RowFilter] | None = None,
    ) -> PaginatedRows:
        """Получить строки таблицы"""
        filters = filters or []

        async with uow_session.start():
            table = await uow_session.tables.get_table_by_id(table_id)
            if not table:
                raise NotFoundException("Таблица не найдена")

            if not await self.permission_service.check_read_access(
                uow_session=uow_session,
                table=table,
                user_id=user_id,
                user_role=user_role,
            ):
                raise AccessDeniedException()

            schema = table.columns_schema or []
            column_names = {c["name"] for c in schema if c.get("name")}
            allowed = column_names | {"id", "created_at", "updated_at"}
            numeric_fields = {
                c["name"] for c in schema if c.get("type") == "number" and c.get("name")
            }

            sort_by = sort_by or "id"
            if sort_by not in allowed:
                raise ValidationException(
                    f"Недопустимая колонка сортировки: '{sort_by}'"
                )

            for f in filters:
                if f.field not in allowed:
                    raise ValidationException(
                        f"Недопустимая колонка фильтра: '{f.field}'"
                    )
                # Числовые сравнения требуют числового значения
                if f.field in numeric_fields and f.op in COMPARISON_OPERATORS:
                    try:
                        float(f.value)
                    except ValueError:
                        raise ValidationException(
                            f"Значение фильтра по '{f.field}' должно быть числом"
                        )
            total = await uow_session.data.count_rows_by_table_id(
                table_id=table_id, filters=filters, numeric_fields=numeric_fields
            )
            rows = await uow_session.data.get_rows_by_table_id(
                table_id=table_id,
                skip=skip,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
                filters=filters,
                numeric_fields=numeric_fields,
            )

            return PaginatedRows(
                items=[self._to_row_response(row) for row in rows],
                total=total,
                skip=skip,
                limit=limit,
            )

    async def get_table_row(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        row_id: int,
    ) -> TableRowResponse | None:
        """Получить строку таблицы"""
        async with uow_session.start():
            table = await uow_session.tables.get_table_by_id(table_id)
            if not table:
                raise NotFoundException("Таблица не найдена")

            if not await self.permission_service.check_read_access(
                uow_session=uow_session,
                table=table,
                user_id=user_id,
                user_role=user_role,
            ):
                raise AccessDeniedException()

            row = await uow_session.data.get_row_by_id(table_id=table_id, row_id=row_id)
            if not row:
                raise NotFoundException()

            return self._to_row_response(row)

    async def create_table_row(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        row_data: TableRowCreate,
    ) -> TableRowResponse:
        """Создать новую строку в таблице"""
        async with uow_session.start():
            table = await uow_session.tables.get_table_by_id(table_id)
            if not table:
                raise NotFoundException("Таблица не найдена")

            if not await self.permission_service.check_write_access(
                uow_session=uow_session,
                table=table,
                user_id=user_id,
                user_role=user_role,
            ):
                raise AccessDeniedException()

            # row_data уже содержит вычисленные значения (фронтенд считает сам)
            validation_errors = self.validation_service.validate_row_data(
                table_columns_schema=table.columns_schema,
                row_data=row_data,
                raise_on_error=False,
            )
            if validation_errors:
                raise ValidationException("; ".join(validation_errors))

            row = await uow_session.data.create_table_row(
                table_id=table_id, row_data=row_data
            )
            logger.info("User %s created row %s in table %s", user_id, row.id, table_id)

            return self._to_row_response(row)

    async def update_table_row(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        row_id: int,
        user_id: int,
        user_role: str,
        row_data: TableRowUpdate,
    ) -> TableRowResponse | None:
        """Обновить строку таблицы"""
        async with uow_session.start():
            table = await uow_session.tables.get_table_by_id(table_id)
            if not table:
                raise NotFoundException("Таблица не найдена")

            if not await self.permission_service.check_write_access(
                uow_session=uow_session,
                table=table,
                user_id=user_id,
                user_role=user_role,
            ):
                logger.warning(
                    "User %s denied write access to table %s", user_id, table_id
                )
                raise AccessDeniedException()

            validation_errors = self.validation_service.validate_row_data(
                table_columns_schema=table.columns_schema,
                row_data=row_data,
                raise_on_error=False,
            )
            if validation_errors:
                raise ValidationException("; ".join(validation_errors))

            row = await uow_session.data.update_table_row(
                table_id=table_id, row_id=row_id, row_data=row_data
            )
            if not row:
                raise NotFoundException()

            return self._to_row_response(row)

    async def delete_table_row(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        row_id: int,
        user_id: int,
        user_role: str,
    ) -> None:
        """Удалить строку таблицы"""
        async with uow_session.start():
            table = await uow_session.tables.get_table_by_id(table_id)
            if not table:
                raise NotFoundException("Таблица не найдена")

            if not await self.permission_service.check_write_access(
                uow_session=uow_session,
                table=table,
                user_id=user_id,
                user_role=user_role,
            ):
                raise AccessDeniedException()

            row = await uow_session.data.get_row_by_id(table_id=table_id, row_id=row_id)
            if not row:
                raise NotFoundException()

            await uow_session.data.delete_table_row(table_id=table_id, row_id=row_id)
            logger.info(
                "User %s deleted row %s from table %s", user_id, row_id, table_id
            )
