from pydantic import BaseModel, field_validator, ConfigDict
from typing import Any
from datetime import datetime


class TableRowBase(BaseModel):
    """Базовая схема для строки таблицы с данными в формате ключ-значение"""

    row_data: dict[str, Any]


class TableRowCreate(TableRowBase):
    """Схема для создания новой строки в таблице"""

    @field_validator("row_data")
    def validate_row_data(cls, v):
        if not isinstance(v, dict):
            raise ValueError("row_data must be a dictionary")
        return v


class TableRowUpdate(TableRowBase):
    """Схема для обновления строки в таблице"""

    @field_validator("row_data")
    def validate_row_data(cls, v):
        """Валидация для обновления - может быть пустым словарем"""
        if not isinstance(v, dict):
            raise ValueError("row_data must be a dictionary")
        return v


class TableRowInDB(TableRowBase):
    """Схема строки таблицы как она хранится в базе данных"""

    id: int
    table_id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TableRowResponse(TableRowInDB):
    """Схема ответа для получения данных строки таблицы"""

    pass
