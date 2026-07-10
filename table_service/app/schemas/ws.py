from datetime import datetime
from enum import Enum
from pydantic import BaseModel

from table_service.app.schemas.data import TableRowResponse


class RowEventType(str, Enum):
    """Типы событий изменения строк таблицы"""

    row_created = "row.created"
    row_updated = "row.updated"
    row_deleted = "row.deleted"


class SRowEvent(BaseModel):
    event: RowEventType
    table_id: int
    row_id: int
    actor_id: int
    row: TableRowResponse | None = None  # None для row.deleted
    occurred_at: datetime


class SWsTicketResponse(BaseModel):
    """Одноразовый тикет для WebSocket-подключения."""

    ticket: str
    expires_in: int
