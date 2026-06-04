import logging
import warnings
from typing import Any
import pandas as pd
from io import BytesIO

from openpyxl.workbook import Workbook

from table_service.app.exceptions import EmptyFileException
from table_service.app.schemas import TableRowCreate

logger = logging.getLogger(__name__)


class ExcelProcessorService:
    """Преобразование DataFrame в схему колонок и строки таблицы. Без доступа к БД."""

    DTYPE_MAP = {
        "int64": "number",
        "int32": "number",
        "int16": "number",
        "int8": "number",
        "float64": "number",
        "float32": "number",
        "float16": "number",
        "bool": "boolean",
        "datetime64[ns]": "datetime",
        "datetime64": "datetime",
        "object": "string",
    }

    COMMON_DATE_FORMATS = [
        "%Y-%m-%d",  # 2024-01-15
        "%d.%m.%Y",  # 15.01.2024
        "%m/%d/%Y",  # 01/15/2024
        "%d/%m/%Y",  # 15/01/2024
        "%Y-%m-%d %H:%M:%S",  # 2024-01-15 14:30:00
        "%d.%m.%Y %H:%M:%S",  # 15.01.2024 14:30:00
        "%m/%d/%Y %H:%M:%S",  # 01/15/2024 14:30:00
        "%Y-%m-%dT%H:%M:%S",  # 2024-01-15T14:30:00
    ]

    def build_columns_schema(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Сгенерировать схему колонок по DataFrame с автоопределением типов."""
        if df.empty or df.columns.empty:
            raise EmptyFileException("Файл не содержит данных для импорта")

        schema = []
        for col in df.columns:
            if pd.isna(col) or str(col).strip() == "":
                continue
            schema.append(
                {
                    "name": str(col),
                    "type": self._infer_column_type(df[col]),
                    "required": False,
                }
            )
        return schema

    def build_rows(self, df: pd.DataFrame) -> tuple[list[TableRowCreate], int]:
        """
        Преобразовать строки DataFrame в объекты для bulk insert.

        Преобразование по типам колонок:
        — числа остаются числами,
        — даты приводятся к ISO-строкам,
        — boolean остаётся boolean,
        — остальное в строки.
        """
        rows, failed = [], 0
        for _, row in df.iterrows():
            try:
                row_data = {
                    str(col): self._convert_value(row[col], str(df[col].dtype))
                    for col in df.columns
                }
                rows.append(TableRowCreate(row_data=row_data))
            except Exception:
                failed += 1
        return rows, failed

    def _infer_column_type(self, series: pd.Series) -> str:
        """Определить тип колонки схемы по dtype и содержимому."""
        dtype = str(series.dtype)
        if dtype == "object":
            return "datetime" if self._is_datetime_column(series) else "string"
        return self.DTYPE_MAP.get(dtype, "string")

    def _convert_value(self, value: Any, dtype: str) -> Any:
        """Привести одно значение к типу, пригодному для хранения."""
        if self._is_na(value):
            return None

        if dtype in ("int64", "int32", "int16", "int8"):
            return int(value)
        if dtype in ("float64", "float32", "float16"):
            return float(value)
        if dtype == "bool":
            return bool(value)
        if "datetime" in dtype:
            return pd.Timestamp(value).isoformat()
        if dtype == "object":
            parsed = self._try_parse_date(value)
            return parsed.isoformat() if parsed is not None else str(value)
        return str(value)

    def _is_datetime_column(self, series: pd.Series) -> bool:
        """
        Проверяет, можно ли преобразовать колонку в datetime.

        Сначала пытается распознать конкретные форматы дат,
        затем только использует общий парсинг.
        """
        sample_values = series.dropna().head(10)
        if len(sample_values) == 0:
            return False

        for date_format in self.COMMON_DATE_FORMATS:
            try:
                pd.to_datetime(sample_values, format=date_format, errors="raise")
                return True
            except (ValueError, TypeError):
                continue

        # Если ни один конкретный формат не подошел, пробуем общий парсинг
        # Но подавляем предупреждение о неопределенном формате
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", category=UserWarning, message="Could not infer format"
                )
                pd.to_datetime(sample_values, errors="raise")
                return True
        except (ValueError, TypeError):
            return False

    def _try_parse_date(self, value: Any) -> pd.Timestamp | None:
        """Попытаться распарсить скалярное значение в дату. None, если не дата."""
        for date_format in self.COMMON_DATE_FORMATS:
            try:
                return pd.to_datetime(value, format=date_format)
            except (ValueError, TypeError):
                continue

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                return pd.to_datetime(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _is_na(value: Any) -> bool:
        """Безопасная проверка на NaN/None для скаляров и нескаляров."""
        try:
            return bool(pd.isna(value))
        except (TypeError, ValueError):
            return False

    def build_workbook(
        self, columns_schema: list[dict[str, Any]], rows: list[dict[str, Any]]
    ) -> BytesIO:
        """
        Построить Excel-файл (.xlsx) из схемы колонок и данных строк.

        Шапка берётся из имён колонок схемы, значения каждой строки
        выбираются по этим именам из row_data (отсутствующие — пустые).
        Возвращает буфер, готовый к отдаче клиенту.
        """
        workbook = Workbook()
        # По умолчанию в новой книге уже есть 1 лист с названием "Sheet"
        # workbook.active возвращает этот лист
        sheet = workbook.active
        column_names = [str(column["name"]) for column in columns_schema]
        sheet.append(column_names)

        for row_data in rows:
            sheet.append([row_data.get(name) for name in column_names])

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer
