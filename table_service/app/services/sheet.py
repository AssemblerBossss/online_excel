import logging
from redis.asyncio import Redis

from table_service.app.schemas import SSheetSnapshot, SSheetBatch, SSheetBatchResult
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.exceptions import (
    NotFoundException,
    LayoutConflictException,
)
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
            if locked is None:
                raise NotFoundException("Таблица не найдена")
            rows = await uow_session.cells.get_all(table_id)
            return SSheetSnapshot(
                table_id=table_id,
                revision=locked.revision,
                layout_revision=locked.layout_revision,
                can_write=can_write,
                meta=locked.sheet_meta or {},
                cells=[[r.row, r.col, r.raw, r.style] for r in rows],
            )

    async def apply_batch(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        batch: SSheetBatch,
    ):
        async with uow_session.start():
            await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )
            table = await uow_session.tables.get_table_for_update(table_id)
            if table is None:
                raise NotFoundException("Таблица не найдена")
            if batch.base_layout_revision != table.layout_revision:
                raise LayoutConflictException()

            op = batch.structural
            if op is not None:
                if op.is_insert:
                    await uow_session.cells.shift(
                        table_id=table_id,
                        axis=op.axis,
                        from_index=op.index,
                        delta=op.count,
                    )
                else:
                    await uow_session.cells.delete_range(
                        table_id=table_id,
                        axis=op.axis,
                        start=op.index,
                        count=op.count,
                    )
            # Дубли (row, col) в одном INSERT ... ON CONFLICT недопустимы: последний выигрывает
            cells = {
                (c.row, c.col): {
                    "row": c.row,
                    "col": c.col,
                    "raw": c.raw,
                    "value": c.value,
                }
                for c in batch.cells
            }

            styles = {
                (s.row, s.col): {
                    "row": s.row,
                    "col": s.col,
                    "style": s.style.to_db() if s.style else None,
                }
                for s in batch.styles
            }
            if cells:
                await uow_session.cells.upsert_cells(table_id, list(cells.values()))
            if styles:
                await uow_session.cells.upsert_styles(table_id, list(styles.values()))

            touched_rows = [r for r, _ in batch.cells] + [r for r, _ in batch.styles]
            if touched_rows:
                await uow_session.cells.delete_empty(
                    table_id=table_id,
                    min_row=min(touched_rows),
                    max_row=max(touched_rows),
                )
            revision, layout_revision = await uow_session.tables.bump_revision(
                table_id, structural=op is not None, meta=batch.meta
            )
        await self._publish(
            table_id,
            user_id,
            batch,
            revision,
            layout_revision,
            len(cells) + len(styles),
        )
        logger.info(
            "User %s applied batch to table %s: rev=%s, cells=%s, styles=%s, structural=%s",
            user_id,
            table_id,
            revision,
            len(cells),
            len(styles),
            op.kind if op else None,
        )
        return SSheetBatchResult(revision=revision, layout_revision=layout_revision)
