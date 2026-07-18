from enum import Enum
from pydantic import BaseModel, field_validator, ConfigDict, Field
from typing import Any
from datetime import datetime


class TableRowBase(BaseModel):
    """Базовая схема для строки таблицы с данными в формате ключ-значение"""

    row_data: dict[str, Any]
    # Исходные формулы ячеек. Ключ — имя колонки, значение — формула ("=5+5").
    # None означает отсутствие формул в строке.
    formulas: dict[str, str] | None = None


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


class FilterOperator(str, Enum):
    """Операторы фильтрации по колонке."""

    eq = "eq"
    ne = "ne"
    contains = "contains"
    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"


# Операторы сравнения требуют, чтобы значение числовой колонки парсилось в число
COMPARISON_OPERATORS = {
    FilterOperator.gt,
    FilterOperator.gte,
    FilterOperator.lt,
    FilterOperator.lte,
}


class RowFilter(BaseModel):
    """Один фильтр: колонка + оператор + значение (как пришло из запроса)."""

    field: str
    op: FilterOperator
    value: str


class PaginatedRows(BaseModel):
    """Страница строк таблицы с метаданными пагинации."""

    items: list[TableRowResponse]
    total: int  # всего строк после фильтрации (без учёта skip/limit)
    skip: int
    limit: int


class BulkDeleteRequest(BaseModel):
    """Список ID для массового удаления строк"""

    row_ids: list[int] = Field(..., min_length=1, max_length=1000)


class BulkDeleteResponse(BaseModel):
    """Сколько строк реально было удалено (может быть меньше len(row_ids),
    если часть уже была удалена параллельно другим пользователем)."""

    deleted_count: int
