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

    model_config = {"extra": "forbid"}
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

    def to_db(self) -> dict[str, Any] | None:
        data = self.model_dump(exclude_none=True)
        return data or None

