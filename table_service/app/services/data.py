import logging
from datetime import UTC, datetime
from typing import Literal
from redis.asyncio import Redis

from table_service.app.services.cache import AccessLevel
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.exceptions import (
    NotFoundException,
    ValidationException,
)
from table_service.app.models import TableRow
from table_service.app.schemas import (
    COMPARISON_OPERATORS,
    PaginatedRows,
    RowEventType,
    RowFilter,
    SRowEvent,
    TableRowCreate,
    TableRowResponse,
    TableRowUpdate,
)
from table_service.app.services.data_validation import DataValidationService
from table_service.app.services.permission import PermissionService
from table_service.app.services.row_events import RowEventPublisher

logger = logging.getLogger(__name__)

ROWS_CACHE_TTL = 60


def _rows_cache_key(table_id: int) -> str:
    return f"rows:table:{table_id}"


class DataService:
    def __init__(
        self,
        redis: Redis,
        permission_service: PermissionService,
        validation_service: DataValidationService | None = None,
        event_publisher: RowEventPublisher | None = None,
    ):
        self.redis = redis
        self.permission_service = permission_service
        self.validation_service = validation_service or DataValidationService()
        self.event_publisher = event_publisher

    @staticmethod
    def _is_default_query(
        skip: int, limit: int, sort_by, sort_order: Literal["asc", "desc"], filters
    ) -> bool:
        return (
            skip == 0
            and limit == 100
            and sort_by is None
            and sort_order == "asc"
            and not filters
        )

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

    async def _invalidate_rows_cache(self, table_id: int) -> None:
        await self.redis.delete(_rows_cache_key(table_id))

    async def _publish_row_event(
        self,
        event: RowEventType,
        table_id: int,
        row_id: int,
        actor_id: int,
        row: TableRowResponse | None,
    ) -> None:
        """Опубликовать событие об изменении строки в Redis для WebSocket-рассылки."""
        if self.event_publisher is None:
            return
        await self.event_publisher.publish(
            SRowEvent(
                event=event,
                table_id=table_id,
                row_id=row_id,
                actor_id=actor_id,
                row=row,
                occurred_at=datetime.now(UTC),
            )
        )

    async def _load_rows(
        self, uow_session, table_id, skip, limit, sort_by, sort_order, filters
    ) -> PaginatedRows:
        """Приватный метод: права тут НЕ проверяются, это делает get_table_rows."""
        async with uow_session.start():
            table = await uow_session.tables.get_table_by_id(table_id=table_id)
            if not table:
                raise NotFoundException("Таблица не найдена")

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
        filters = filters or []

        # 1. Доступ: ВСЕГДА, для любых параметров запроса, один раз, с кэшем.
        #    Вызываем ДО `async with uow_session.start()`, не внутри.
        await self.permission_service.ensure_access(
            uow_session=uow_session,
            table_id=table_id,
            user_id=user_id,
            user_role=user_role,
            level=AccessLevel.READ,
        )

        # 2. Кэш строк (общий для всех пользователей, т.к. доступ уже проверен)
        use_cache = self._is_default_query(skip, limit, sort_by, sort_order, filters)
        if use_cache:
            cached = await self.redis.get(_rows_cache_key(table_id))
            if cached:
                return PaginatedRows.model_validate_json(cached)

        # 3. БД
        result = await self._load_rows(
            uow_session, table_id, skip, limit, sort_by, sort_order, filters
        )

        if use_cache:
            await self.redis.setex(
                _rows_cache_key(table_id), ROWS_CACHE_TTL, result.model_dump_json()
            )
        return result

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
            await self.permission_service.get_table_with_read_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

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
            table = await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

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

            response = self._to_row_response(row)

        await self._invalidate_rows_cache(table_id)
        await self._publish_row_event(
            event=RowEventType.row_created,
            table_id=table_id,
            row_id=response.id,
            actor_id=user_id,
            row=response,
        )
        return response

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
            table = await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

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

            response = self._to_row_response(row)

        await self._invalidate_rows_cache(table_id)
        await self._publish_row_event(
            event=RowEventType.row_updated,
            table_id=table_id,
            row_id=response.id,
            actor_id=user_id,
            row=response,
        )
        return response

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
            await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            row = await uow_session.data.get_row_by_id(table_id=table_id, row_id=row_id)
            if not row:
                raise NotFoundException()

            await uow_session.data.delete_table_row(table_id=table_id, row_id=row_id)
            logger.info(
                "User %s deleted row %s from table %s", user_id, row_id, table_id
            )

        await self._invalidate_rows_cache(table_id)
        await self._publish_row_event(
            event=RowEventType.row_deleted,
            table_id=table_id,
            row_id=row_id,
            actor_id=user_id,
            row=None,
        )

    async def duplicate_table_row(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        row_id: int,
        user_id: int,
        user_role: str,
    ) -> TableRowResponse:
        """Дублировать строку таблицы"""
        async with uow_session.start():
            await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            original = await uow_session.data.get_row_by_id(
                table_id=table_id, row_id=row_id
            )
            if not original:
                raise NotFoundException("Строка не найдена")

            # Валидацию не повторяем - данные уже валидны, раз хранятся в БД
            copy_data = TableRowCreate(
                row_data=original.row_data,
                formulas=original.formulas,
            )

            new_row = await uow_session.data.create_table_row(
                table_id=table_id, row_data=copy_data
            )

            logger.info(
                "User %s duplicated row %s -> %s in table %s",
                user_id,
                row_id,
                new_row.id,
                table_id,
            )
            response = self._to_row_response(new_row)

        await self._invalidate_rows_cache(table_id)
        # Публикуем как обычное создание строки — у соавторов таблицы,
        # смотрящих её сейчас через WS, копия появится в реальном времени.
        await self._publish_row_event(
            event=RowEventType.row_created,
            table_id=table_id,
            row_id=response.id,
            actor_id=user_id,
            row=response,
        )

        return response

    async def bulk_delete_table_rows(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        row_ids: list[int],
        user_id: int,
        user_role: str,
    ) -> int:
        """Удалить несколько строк таблицы одним запросом"""
        async with uow_session.start():
            await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            deleted_ids = await uow_session.data.bulk_delete_table_rows(
                table_id=table_id, row_ids=row_ids
            )
            logger.info(
                "User %s bulk-deleted %s/%s rows from table %s",
                user_id,
                len(deleted_ids),
                len(row_ids),
                table_id,
            )
        if deleted_ids:
            await self._invalidate_rows_cache(table_id)

        for row_id in deleted_ids:
            await self._publish_row_event(
                event=RowEventType.row_deleted,
                table_id=table_id,
                row_id=row_id,
                actor_id=user_id,
                row=None,
            )
        return len(deleted_ids)
