from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field


class DataTableBase(BaseModel):
    """Базовая схема для таблицы с данными"""

    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


class DataTableUpdate(DataTableBase):
    """Схема для обновления таблицы"""


class DataTableCreate(BaseModel):
    """Схема для создания новой таблицы"""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_public: bool = False
    columns_schema: list[dict[str, Any]] = Field(default_factory=list)


class DataTableResponse(DataTableBase):
    """Схема ответа для получения таблицы"""

    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime | None = None
    columns_schema: list[dict[str, Any]] | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    is_pinned: bool = False


class DataTableDuplicate(BaseModel):
    """Параметры клонирования таблицы"""

    with_rows: bool | None = None
    name: str | None = None
