from redis.asyncio import Redis

from core.export_storage import ExportStorage
from schemas import SExportJob
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
        return f"export:job:{job_id}"

    async def _save(self, job: SExportJob) -> None:
        await self.redis.setex(
            name=self._key(job.job_id), time=JOB_TTL, value=job.model_dump_json()
        )
