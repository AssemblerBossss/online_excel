from pydantic import BaseModel, field_validator
from typing import Dict, Any, Optional, List
from datetime import datetime


class DataTableBase(BaseModel):
    """Базовая схема для таблицы с данными"""

    name: str
    description: Optional[str] = None
    is_public: Optional[bool] = False
    columns_schema: Optional[dict[str, Any]] = None


class DataTableCreate(DataTableBase):
    """Схема для создания новой таблицы"""

    pass


class DataTableResponse(DataTableBase):
    """Схема ответа для получения таблицы"""

    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
