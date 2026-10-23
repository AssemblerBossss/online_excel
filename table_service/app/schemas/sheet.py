from datetime import datetime
from typing import Literal, Any

from pydantic import BaseModel, Field, field_serializer, field_validator

# Лимиты листа. Те же числа продублированы на фронте (frontend/src/sheet/address.ts).
MAX_ROWS = 100_000
MAX_COLS = 1_000
MAX_BATCH_ITEMS = 20_000
MAX_RAW_LENGTH = 50_000
MAX_CELLS_IN_EVENT = 2_000

HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class SCellStyle(BaseModel):
    """Оформление ячейки"""

    bg: str | None = Field(default=None, pattern=HEX_COLOR)
    fg: str | None = Field(default=None, pattern=HEX_COLOR)
    bold: bool | None = None
    italic: bool | None = None
    halign: Literal["left", "center", "right"] | None = None
    wrap: bool | None = None
    numFmt: (
        Literal["general", "number", "percent", "currency", "date", "datetime"] | None
    ) = None
    decimals: int | None = Field(default=None, ge=0, le=10)

    model_config = {"extra": "forbid"}

    def to_db(self) -> dict[str, Any] | None:
        data = self.model_dump(exclude_none=True)
        return data or None


class SCellWrite(BaseModel):
    """Данные для записи одной ячейки (координаты, значение, raw-строка)."""

    row: int = Field(ge=0, lt=MAX_ROWS)
    col: int = Field(ge=0, lt=MAX_COLS)
    raw: str | None = Field(default=None, max_length=MAX_RAW_LENGTH)
    value: Any = None

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Any) -> Any:
        if v is None or isinstance(v, str | int | float | bool):
            return v
        if isinstance(v, dict) and set(v) == {"e"} and isinstance(v["e"], str):
            return v
        raise ValueError("value: ожидается число, строка, bool, null или {'e': '#ERR'}")


class SStyleWrite(BaseModel):
    """Данные для изменения стиля конкретной ячейки."""

    row: int = Field(ge=0, lt=MAX_ROWS)
    col: int = Field(ge=0, lt=MAX_COLS)
    style: SCellStyle | None = None

    @field_serializer("style")
    def serialize_style(self, style: SCellStyle | None) -> dict[str, Any] | None:
        """В JSON (события WS) уходят только заданные свойства, без null."""
        return style.to_db() if style else None


class SStructuralOp(BaseModel):
    """Структурная операция: вставка или удаление строк/колонок."""

    kind: Literal["insert_rows", "delete_rows", "insert_cols", "delete_cols"]
    index: int = Field(ge=0)
    count: int = Field(ge=1, le=MAX_ROWS)

    @property
    def axis(self) -> Literal["row", "col"]:
        return "row" if self.kind.endswith("rows") else "col"

    @property
    def is_insert(self) -> bool:
        return self.kind.startswith("insert")


class SSheetBatch(BaseModel):
    """Пакет изменений листа: (опц.) структурная операция, затем ячейки, оформление, meta."""

    client_id: int = Field(min_length=1, max_length=64)
    base_layout_revision: int = Field(ge=0)
    structural: SStructuralOp | None = None
    cells: list[SCellWrite] = Field(default_factory=list, max_length=MAX_BATCH_ITEMS)
    styles: list[SStyleWrite] = Field(default_factory=list, max_length=MAX_BATCH_ITEMS)
    # Полная замена meta (ширины колонок, оформление целых строк/колонок, закрепление)
    meta: dict[str, Any] | None = None

    @field_validator("meta")
    @classmethod
    def validate_meta(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None and len(str(v)) > 200_000:
            raise ValueError("meta слишком большая")
        return v


class SSheetBatchResult(BaseModel):
    """Результат применения пакета изменений."""

    revision: int
    layout_revision: int


class SSheetSnapshot(BaseModel):
    """Снимок состояния листа при первоначальной загрузке."""

    table_id: int
    revision: int
    layout_revision: int
    meta: dict[str, Any]
    # Компактный формат: [row, col, raw, value, style]
    cells: list[list[Any]]


class SSheetEvent(BaseModel):
    """Событие, рассылаемое всем подписчикам листа через Redis Pub/Sub -> WebSocket."""

    kind: Literal["batch", "reload"]
    table_id: int
    revision: int
    layout_revision: int
    actor_id: int
    client_id: str
    structural: SStructuralOp | None = None
    cells: list[SCellWrite] = Field(default_factory=list)
    styles: list[SStyleWrite] = Field(default_factory=list)
    meta: dict[str, Any] | None = None
    occurred_at: datetime
