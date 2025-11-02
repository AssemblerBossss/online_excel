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
            type: "string",
            "required": False,
        }
        columns_schemas.append(columns_schema)

    return columns_schemas


async def _import_excel_data_to_table(
    data_repo: DataRepository, table_id: int, df: pd.DataFrame
) -> None:
    for _, row in df.iterrows():
        try:
            row_data = {
                str(col): str(row[col]) if not pd.isna(row[col]) else None
                for col in df.columns
            }
            row_create = TableRowCreate(row_data=row_data)
            await data_repo.create_table_row(table_id, row_create)

        except Exception as e:
            # logger.warning(f"Не удалось импортировать строку: {str(e)}")
            continue
