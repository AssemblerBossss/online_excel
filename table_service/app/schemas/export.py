from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class ExportJobStatus(str, Enum):
    job_pending = "pending"
    job_running = "running"
    job_completed = "completed"
    job_error = "error"


class SExportJob(BaseModel):
    job_id: int
    table_id: int
    author_id: int
    filename: str
    status: ExportJobStatus = ExportJobStatus.job_pending
    object_name: str | None = None
    error: str | None = None


class SExportJobCreated(BaseModel):
    job_id: int
    status: ExportJobStatus = ExportJobStatus.job_pending


class SExportJobStatusResponse(BaseModel):
    job_id: int
    filename: str
    status: ExportJobStatus = ExportJobStatus.job_pending
    download_url: str | None = None  # заполнен только при status=done
    error: str | None = None
