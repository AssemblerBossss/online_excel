import json
import uuid

from redis.asyncio import Redis

from schemas import ExportJobStatus
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.core import ExportStorage
from table_service.app.exceptions import (
    ExportJobNotFoundException,
    NotFoundException,
    AccessDeniedException,
)
from table_service.app.schemas import SExportJob, SExportJobCreated, SCurrentUser
from table_service.app.services.permission import PermissionService
from table_service.app.services.excel_processor import ExcelProcessorService

JOB_TTL = 3600


class ExportJobService:
    """Фоновый экспорт таблиц в Excel: постановка, выполнение, опрос статуса."""

    def __init__(
        self,
        redis: Redis,
        storage: ExportStorage,
        permission_service: PermissionService,
        excel_processor: ExcelProcessorService,
    ):
        self.redis = redis
        self.storage = storage
        self.permission_service = permission_service
        self.excel_processor = excel_processor

    @staticmethod
    def _key(job_id: str) -> str:
        """Сформировать ключ Redis для задачи экспорта."""
        return f"export:job:{job_id}"

    async def _save(self, job: SExportJob) -> None:
        """Сохранить задачу экспорта в Redis с TTL."""
        await self.redis.setex(
            name=self._key(job.job_id), time=JOB_TTL, value=job.model_dump_json()
        )

    async def _load(self, job_id: str) -> SExportJob:
        """Загрузить задачу экспорта из Redis по ID."""
        job = await self.redis.get(self._key(job_id))
        if job is None:
            raise ExportJobNotFoundException()
        return SExportJob.model_validate(json.loads(job))

    async def start(
        self,
        uow_session: UnitOfWork,
        current_user: SCurrentUser,
        table_id: int,
        user_role: str,
    ) -> SExportJobCreated:
        async with uow_session.start():
            table = await uow_session.tables.get_table_by_id(table_id)
            if not table:
                raise NotFoundException("Таблица не найдена")
            if not await self.permission_service.check_read_access(
                uow_session=uow_session,
                table=table,
                user_id=current_user.user_id,
                user_role=user_role,
            ):
                raise AccessDeniedException()
            filename = f"{table.name}.xlsx"

        job = SExportJob(
            job_id=uuid.uuid4().hex,
            table_id=table_id,
            author_id=current_user.user_id,
            status=ExportJobStatus.job_pending,
            filename=filename,
        )

        await self._save(job)
        return SExportJobCreated(job_id=job.job_id, status=job.status)
