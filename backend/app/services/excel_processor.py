from typing import Any
import pandas as pd

from backend.app.repository import DataRepository
from backend.app.schemas import DataTableCreate, TableRowCreate


def _generate_columns_schema_from_dataframe(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]] | None:
    if dataframe.empty or dataframe.columns.empty:
        return None

    columns_schemas = []

    for column_name in dataframe.columns:
        if pd.isna(column_name) or str(column_name).strip() == "":
            continue

        columns_schema = {
            "name": str(column_name),
            "type": "string",
            "required": False,
        }
        columns_schemas.append(columns_schema)

    return columns_schemas


async def _import_excel_data_to_table(
    data_repo: DataRepository, table_id: int, df: pd.DataFrame
) -> dict[str, int]:
    """
    Импортирует данные из DataFrame в таблицу используя bulk insert.

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
            row_data = {
                str(col): str(row[col]) if not pd.isna(row[col]) else None
                for col in df.columns
            }
            row_create = TableRowCreate(row_data=row_data)
            rows_to_create.append(row_create)

        except Exception as e:
            # logger.warning(f"Не удалось импортировать строку: {str(e)}")
            failed_count += 1
            continue
    if rows_to_create:
        created_count = await data_repo.bulk_create_table_row(
            table_id=table_id, rows_data=rows_to_create
        )
    else:
        created_count = 0

    return {"total": len(df), "success": created_count, "failed": failed_count}
