import asyncio
import json
import logging
import uuid

from io import BytesIO
from redis.asyncio import Redis

from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.core import ExportStorage
from table_service.app.exceptions import (
    ExportJobNotFoundException,
    NotFoundException,
    AccessDeniedException,
)
from table_service.app.schemas import (
    SExportJob,
    SExportJobCreated,
    SCurrentUser,
    ExportJobStatus,
)
from table_service.app.services.permission import PermissionService
from table_service.app.services.excel_processor import ExcelProcessorService

JOB_TTL = 3600
CHUNK_SIZE = 4000
logger = logging.getLogger(__name__)


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
        """Создать задачу экспорта с проверкой прав и сохранить в Redis со статусом pending."""
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

    async def run(self, job_id: str, uow_session: UnitOfWork) -> SExportJob:
        job = await self._load(job_id)
        job.status = ExportJobStatus.job_running
        await self._save(job)

        try:
            buffer, total_rows = await self._build_file(uow_session, job.table_id)
            object_name = f"tables/{job.table_id}/{job.job_id}.xlsx"

            await self.storage.upload_excel_file(
                object_name=object_name,
                content=buffer,
                length=buffer.getbuffer().nbytes,
            )

            job.object_name = object_name
            job.status = ExportJobStatus.job_completed
            await self._save(job)
            logger.info(
                "Export job %s finished: table %s, %s rows",
                job.job_id,
                job.table_id,
                total_rows,
            )
        except Exception as e:
            logger.exception("Export job %s failed", job.job_id)
            job.status = ExportJobStatus.job_error
            job.error = str(e)
            await self._save(job)

    async def _build_file(
        self, uow_session: UnitOfWork, table_id: int
    ) -> tuple[BytesIO, int]:
        async with uow_session.start():
            table = await uow_session.tables.get_table_by_id(table_id)
            if not table:
                raise NotFoundException("Таблица не найдена")

            workbook, sheet, column_names = (
                self.excel_processor.create_streaming_workbook(table.columns_schema)
            )

            total_rows = 0
            chunk: list[dict] = []

            async for row in uow_session.data.stream_rows_by_table_id(
                table_id=table_id, chunk_size=CHUNK_SIZE
            ):
                chunk.append(row)
                if len(chunk) > CHUNK_SIZE:
                    await asyncio.to_thread(
                        self.excel_processor.append_rows_chunk,
                        sheet,
                        column_names,
                        chunk,
                    )
                    total_rows += len(chunk)
                    chunk = []
            if chunk:
                await asyncio.to_thread(
                    self.excel_processor.append_rows_chunk, sheet, column_names, chunk
                )
                total_rows += len(chunk)
        buffer = await asyncio.to_thread(
            self.excel_processor.finalize_workbook, workbook
        )

        return buffer, total_rows
