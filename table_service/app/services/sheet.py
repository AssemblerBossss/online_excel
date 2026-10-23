import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from redis.asyncio import Redis

from schemas import SSheetSnapshot
from table_service.app.services.cache import AccessLevel
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.exceptions import (
    NotFoundException,
    ValidationException,
)
from table_service.app.models import SheetCell


from table_service.app.services.data_validation import DataValidationService
from table_service.app.services.permission import PermissionService
from table_service.app.services.sheet_events import SheetEventPublisher


logger = logging.getLogger(__name__)


class SheetService:
    """Лист таблицы: снимок для клиента и применение пакетов изменений."""

    def __init__(
        self,
        redis: Redis,
        permission_service: PermissionService,
        event_publisher: SheetEventPublisher | None = None,
    ):
        self.redis = redis
        self.permission_service = permission_service
        self.event_publisher = event_publisher

    async def get_snapshot(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> SSheetSnapshot:

        async with uow_session.start():
            table = await self.permission_service.get_table_with_read_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )
            can_write = await self.permission_service.check_write_access(
                uow_session=uow_session,
                table=table,
                user_id=user_id,
                user_role=user_role,
            )
            locked = await uow_session.tables.get_table_for_share(table_id)
            if not locked:
                raise NotFoundException("Таблица не найдена")
            rows = await uow_session.cells.get_all(table_id)
            return SSheetSnapshot(
                table_id=table_id,
                revision=locked.revision,
                layout_revision=locked.layout_revision,
                meta=locked.sheet_meta or {},
                cells=[[r.row, r.col, r.raw, r.style] for r in rows],
            )
