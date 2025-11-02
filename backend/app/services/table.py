from fastapi import UploadFile, HTTPException
from starlette import status
import pandas as pd

from backend.app.schemas import DataTableResponse, DataTableCreate
from backend.app.repository import TableRepository
from .excel_processor import (
    _generate_columns_schema_from_dataframe,
    _import_excel_data_to_table,
)


class TableService:

    def __init__(self, table_repository: TableRepository):
        self.table_repo = table_repository

    async def create_table(
        self, table_data: DataTableCreate, user_id: int
    ) -> DataTableResponse:
        """
        Создать новую таблицу

        Args:
            table_data: Данные для создания таблицы
            user_id: ID пользователя-создателя

        Returns:
            DataTableResponse: Созданная таблица
        """

        table = await self.table_repo.create_table(table_data, user_id)

        if not table:
            raise Exception("Не удалось создать таблицу")

        return DataTableResponse(
            id=table.id,
            name=table.name,
            description=table.description,
            is_public=table.is_public,
            columns_schema=table.columns_schema,
            created_by=table.created_by_id,
            created_at=table.created_at,
            updated_at=table.updated_at,
        )

    async def create_table_from_excel_file(
        self, excel_file: UploadFile, user_id: int, table_name: str = None
    ) -> DataTableResponse:
        """
        Создать новую таблицу из Excel файла

        Args:
            excel_file: Excel файл для создания таблицы
            user_id: ID пользователя-создателя
            table_name: Название таблицы (если None - используется имя файла)

        Returns:
            DataTableResponse: Созданная таблица
        """
        # Валидация файла
        if not excel_file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(
                400, "Файл должен быть в формате Excel (.xlsx или .xls)"
            )

        try:
            df = pd.read_excel(excel_file.file)

            # Если название таблицы не указано, используем имя файла без расширения
            if table_name is None:
                table_name = excel_file.filename.rsplit(".", 1)[0]

            # Генерация схемы колонок на основе DataFrame
            columns_schema = _generate_columns_schema_from_dataframe(df)

            table_data = DataTableCreate(
                name=table_name,
                description=f"Таблица создана из файла {excel_file.filename}",
                is_public=False,
                columns_schema=columns_schema,
            )

            table = await self.table_repo.create_table(table_data, user_id)

            if not table:
                raise Exception("Не удалось создать таблицу из Excel файла")

            await _import_excel_data_to_table(table.id, df)

            return DataTableResponse(
                id=table.id,
                name=table.name,
                description=table.description,
                is_public=table.is_public,
                columns_schema=table.columns_schema,
                created_by=table.created_by_id,
                created_at=table.created_at,
                updated_at=table.updated_at,
            )

        except pd.errors.EmptyDataError:
            raise HTTPException(400, "Excel файл пустой")
        except pd.errors.ParserError:
            raise HTTPException(400, "Ошибка парсинга Excel файла")
        except Exception as e:
            raise HTTPException(500, f"Ошибка обработки Excel файла: {str(e)}")
