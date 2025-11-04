from typing import List, Optional
from fastapi import UploadFile, HTTPException
import pandas as pd

from backend.app.schemas import DataTableResponse, DataTableCreate
from backend.app.repository import TableRepository, DataRepository
from .excel_processor import (
    _generate_columns_schema_from_dataframe,
    _import_excel_data_to_table,
)


class TableService:

    def __init__(
        self, table_repository: TableRepository, data_repository: DataRepository
    ):
        self.table_repo = table_repository
        self.data_repo = data_repository

    def _to_response(self, table) -> DataTableResponse:
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

    async def get_all_tables(self) -> List[DataTableResponse]:
        """
        Получить список всtх таблиц
        Returns:
            List[DataTableResponse]: Список таблиц
        """
        tables = await self.table_repo.get_all_tables()
        if not tables:
            return []
        return [self._to_response(table) for table in tables]

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

        return self._to_response(table)

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

            await _import_excel_data_to_table(self.data_repo, table.id, df)

            return self._to_response(table)

        except pd.errors.EmptyDataError:
            raise HTTPException(400, "Excel файл пустой")
        except pd.errors.ParserError:
            raise HTTPException(400, "Ошибка парсинга Excel файла")
        except Exception as e:
            raise HTTPException(500, f"Ошибка обработки Excel файла: {str(e)}")
