import json
from redis.asyncio import Redis

from table_service.app.core import ExportStorage
from table_service.app.exceptions import ExportJobNotFoundException
from table_service.app.schemas import SExportJob
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
