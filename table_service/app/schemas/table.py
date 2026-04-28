from pydantic import BaseModel
from typing import Any
from datetime import datetime


class DataTableBase(BaseModel):
    """Базовая схема для таблицы с данными"""

    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


class DataTableUpdate(DataTableBase):
    pass


class DataTableCreate(DataTableBase):
    """Схема для создания новой таблицы"""

    columns_schema: list[dict[str, Any]] | None = None


class DataTableResponse(DataTableBase):
    """Схема ответа для получения таблицы"""

    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime | None = None
    columns_schema: list[dict[str, Any]] | None = None
