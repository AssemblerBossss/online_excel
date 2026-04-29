import warnings
from typing import Any
import pandas as pd

from table_service.app.repository import DataRepository
from table_service.app.schemas import DataTableCreate, TableRowCreate


# Маппинг pandas dtype на типы схемы
dtype_map = {
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

# Распространенные форматы дат для проверки
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


def _is_datetime_column(series: pd.Series) -> bool:
    """
    Проверяет, можно ли преобразовать колонку в datetime.

    Сначала пытается распознать конкретные форматы дат,
    затем только использует общий парсинг.
    """
    sample_values = series.dropna().head(10)

    if len(sample_values) == 0:
        return False

    # Пробуем распознать конкретные форматы дат
    for date_format in COMMON_DATE_FORMATS:
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


def _generate_columns_schema_from_dataframe(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]] | None:
    """
    Генерирует схему колонок на основе DataFrame с автоматическим определением типов.

    Args:
        dataframe: DataFrame для анализа

    Returns:
        Список схем колонок с определенными типами данных
    """

    if dataframe.empty or dataframe.columns.empty:
        return None

    columns_schemas = []

    for column_name in dataframe.columns:
        if pd.isna(column_name) or str(column_name).strip() == "":
            continue

        # Получаем тип данных колонки
        dtype = str(dataframe[column_name].dtype)
        schema_type = dtype_map.get(dtype, "string")

        if dtype == "object":
            # Проверяем, можно ли преобразовать в дату
            if _is_datetime_column(dataframe[column_name]):
                schema_type = "datetime"
            else:
                schema_type = "string"

        columns_schema = {
            "name": str(column_name),
            "type": schema_type,
            "required": False,
        }
        columns_schemas.append(columns_schema)

    return columns_schemas


async def _import_excel_data_to_table(
    data_repo: DataRepository, table_id: int, df: pd.DataFrame
) -> dict[str, int]:
    """
    Импортирует данные из DataFrame в таблицу используя bulk insert.

    Преобразует данные в соответствии с их типами:
    - Числа остаются числами
    - Даты преобразуются в ISO строки
    - Boolean остаются boolean
    - Остальное в строки

    Args:
        data_repo: Репозиторий для работы с данными
        table_id: ID таблицы
        df: DataFrame с данными для импорта

    Returns:
        dict: Статистика импорта {"total": N, "success": M, "failed": K}
    """

    rows_to_create = []
    failed_count = 0

    for idx, row in df.iterrows():
        try:
            row_data = {}

            for col in df.columns:
                value = row[col]

                # Пропускаем NaN/None значения
                if pd.isna(value):
                    row_data[str(col)] = None
                    continue

                # Определяем тип данных и преобразуем соответственно
                col_dtype = str(df[col].dtype)

                # Числовые типы
                if col_dtype in ["int64", "int32", "int16", "int8"]:
                    row_data[str(col)] = int(value)
                elif col_dtype in ["float64", "float32", "float16"]:
                    row_data[str(col)] = float(value)
                # Boolean
                elif col_dtype == "bool":
                    row_data[str(col)] = bool(value)
                # Datetime
                elif "datetime" in col_dtype:
                    row_data[str(col)] = pd.Timestamp(value).isoformat()
                # Object - может быть дата или строка
                elif col_dtype == "object":
                    # Пытаемся преобразовать в дату
                    try:
                        # Сначала пробуем распознать формат
                        date_val = None
                        for date_format in COMMON_DATE_FORMATS:
                            try:
                                date_val = pd.to_datetime(value, format=date_format)
                                break
                            except (ValueError, TypeError):
                                continue

                        # Если не подошел ни один формат, пробуем общий парсинг
                        if date_val is None:
                            with warnings.catch_warnings():
                                warnings.filterwarnings("ignore", category=UserWarning)
                                date_val = pd.to_datetime(value)

                        row_data[str(col)] = date_val.isoformat()
                    except (ValueError, TypeError):
                        # Если не дата, то строка
                        row_data[str(col)] = str(value)
                else:
                    # По умолчанию строка
                    row_data[str(col)] = str(value)

            row_create = TableRowCreate(row_data=row_data)
            rows_to_create.append(row_create)

        except Exception as e:
            # logger.warning(f"Не удалось импортировать строку {idx}: {str(e)}")
            failed_count += 1
            continue

    if rows_to_create:
        created_count = await data_repo.bulk_create_table_row(
            table_id=table_id, rows_data=rows_to_create
        )
    else:
        created_count = 0

    return {"total": len(df), "success": created_count, "failed": failed_count}
