from datetime import datetime
from typing import Optional, Literal, List, Any

from backend.app.models import DataTable
from backend.app.schemas import TableRowResponse, TableRowCreate, TableRowUpdate
from backend.app.repository import DataRepository, TableRepository
from backend.app.exceptions import (
    AccessDeniedException,
    ValidationException,
    NotFoundException,
)


class DataService:

    def __init__(self, data_repo: DataRepository, table_repo: TableRepository):
        self.data_repo = data_repo
        self.table_repo = table_repo

    def _validate_row_data_with_schema(
        self,
        table_columns_schema: list[dict[str, Any]],
        row_data: TableRowCreate | TableRowUpdate,
    ) -> list[str]:
        """
        Валидация данных строки по схеме таблицы

        Args:
            table_columns_schema: Схема колонок таблицы
            row_data: Данные строки для валидации

        Returns:
            list[str]: Список ошибок валидации (пустой если ошибок нет)
        """
        errors = []

        if not table_columns_schema:
            return errors

        schema_dict = {
            col_schema.get("name"): col_schema
            for col_schema in table_columns_schema
            if col_schema.get("name")
        }

        # Проверка обязательных полей
        for col_name, col_schema in schema_dict.items():
            if col_schema.get("required", False) and col_name not in row_data.columns:
                errors.append(f"Обязательное поле '{col_name}' отсутствует")

        # Проверка типов данных
        for col_name, value in row_data.row_data.items():
            if col_name not in schema_dict:
                continue

            col_schema = schema_dict[col_name]
            expected_type = col_schema.get("type", "string")

            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Поле {col_name} должно быть строкой")
            elif expected_type == "number" and not isinstance(value, int):
                errors.append(f"Поле {col_name} должно быть числом")
            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Поле {col_name} должно быть булевым")
            elif expected_type == "date":
                date_error = self._validate_date_field(value, col_name, col_schema)
                if date_error:
                    errors.append(date_error)

            elif expected_type == "datetime":
                datetime_error = self._validate_datetime_field(
                    value, col_name, col_schema
                )
                if datetime_error:
                    errors.append(datetime_error)

        # Проверяем ограничения значений (остальная логика)
        for col_name, value in row_data.row_data.items():
            if col_name not in schema_dict:
                continue

            col_schema = schema_dict[col_name]

            # Проверка минимального/максимального значения для чисел
            if isinstance(value, (int, float)):
                if "min_value" in col_schema and value < col_schema["min_value"]:
                    errors.append(
                        f"Значение поля '{col_name}' не может быть меньше {col_schema['min_value']}"
                    )
                if "max_value" in col_schema and value > col_schema["max_value"]:
                    errors.append(
                        f"Значение поля '{col_name}' не может быть больше {col_schema['max_value']}"
                    )

            # Проверка длины для строк
            if isinstance(value, str):
                if "min_length" in col_schema and len(value) < col_schema["min_length"]:
                    errors.append(
                        f"Длина поля '{col_name}' не может быть меньше {col_schema['min_length']} символов"
                    )
                if "max_length" in col_schema and len(value) > col_schema["max_length"]:
                    errors.append(
                        f"Длина поля '{col_name}' не может быть больше {col_schema['max_length']} символов"
                    )

            # Проверка по enum (допустимые значения)
            if "enum" in col_schema and value not in col_schema["enum"]:
                errors.append(
                    f"Значение поля '{col_name}' должно быть одним из: {', '.join(col_schema['enum'])}"
                )

        return errors

    @staticmethod
    def _validate_date_field(
        value: Any, col_name: str, col_schema: dict
    ) -> Optional[str]:
        """Валидация поля типа 'date'"""
        if isinstance(value, str):
            try:
                # Пробуем разные форматы дат
                date_formats = col_schema.get(
                    "date_formats", ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y.%m.%d"]
                )

                parsed_date = None
                for date_format in date_formats:
                    try:
                        parsed_date = datetime.strptime(value, date_format).date()
                        break
                    except ValueError:
                        continue

                if not parsed_date:
                    return f"Поле '{col_name}' имеет неверный формат даты. Ожидаемые форматы: {', '.join(date_formats)}"

                # Проверка диапазона дат если указано
                if "min_date" in col_schema:
                    min_date = datetime.strptime(
                        col_schema["min_date"], "%Y-%m-%d"
                    ).date()
                    if parsed_date < min_date:
                        return f"Дата в поле '{col_name}' не может быть раньше {col_schema['min_date']}"

                if "max_date" in col_schema:
                    max_date = datetime.strptime(
                        col_schema["max_date"], "%Y-%m-%d"
                    ).date()
                    if parsed_date > max_date:
                        return f"Дата в поле '{col_name}' не может быть позже {col_schema['max_date']}"

            except ValueError as e:
                return f"Поле '{col_name}' содержит невалидную дату: {str(e)}"
        else:
            return f"Поле '{col_name}' должно быть строкой с датой"

        return None

    @staticmethod
    def _validate_datetime_field(
        value: Any, col_name: str, col_schema: dict
    ) -> Optional[str]:
        """
        Валидация поля типа 'datetime'
        """
        if isinstance(value, str):
            try:
                # Разные форматы даты и времени
                datetime_formats = col_schema.get(
                    "datetime_formats",
                    [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S",
                        "%d.%m.%Y %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                        "%d.%m.%Y %H:%M",
                    ],
                )

                parsed_datetime = None
                for datetime_format in datetime_formats:
                    try:
                        parsed_datetime = datetime.strptime(value, datetime_format)
                        break
                    except ValueError:
                        continue

                if not parsed_datetime:
                    return f"Поле '{col_name}' имеет неверный формат даты и времени. Ожидаемые форматы: {', '.join(datetime_formats)}"

                # Проверка диапазона datetime если указано
                if "min_datetime" in col_schema:
                    min_dt = datetime.strptime(
                        col_schema["min_datetime"], "%Y-%m-%d %H:%M:%S"
                    )
                    if parsed_datetime < min_dt:
                        return f"Дата/время в поле '{col_name}' не может быть раньше {col_schema['min_datetime']}"

                if "max_datetime" in col_schema:
                    max_dt = datetime.strptime(
                        col_schema["max_datetime"], "%Y-%m-%d %H:%M:%S"
                    )
                    if parsed_datetime > max_dt:
                        return f"Дата/время в поле '{col_name}' не может быть позже {col_schema['max_datetime']}"

            except ValueError as e:
                return f"Поле '{col_name}' содержит невалидную дату/время: {str(e)}"
        else:
            return f"Поле '{col_name}' должно быть строкой с датой и временем"

        return None

    async def get_table_rows(
        self,
        table_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> List[TableRowResponse]:
        """Получить строки таблицы"""

        table = await self.table_repo.get_table_with_read_access(
            table_id=table_id, user_id=user_id
        )

        if not table:
            raise AccessDeniedException

        if not sort_by:
            sort_by = "id"

        rows = await self.data_repo.get_rows_by_table_id(
            table_id=table_id,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return [
            TableRowResponse(
                id=row.id,
                table_id=row.table_id,
                row_data=row.row_data,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def get_table_row(
        self, table_id: int, user_id: int, row_id: int
    ) -> List[TableRowResponse]:
        """Получить строку таблицы"""

        pass
        # table = await self.table_repo.get_table_with_access(
        #     table_id=table_id, user_id=user_id
        # )
        #
        # if not table:
        #     raise AccessDeniedException
        #
        # rows = await self.data_repo.get_rows_by_table_id(
        #     table_id, skip, limit, sort_by, sort_order
        # )
        #
        # return [
        #     TableRowResponse(
        #         id=row.id,
        #         table_id=row.table_id,
        #         row_data=row.row_data,
        #         created_at=row.created_at,
        #         updated_at=row.updated_at,
        #     )
        #     for row in rows
        # ]

    async def create_table_row(
        self, table_id: int, user_id: int, row_data: TableRowCreate
    ) -> TableRowResponse:
        """Создать новую строку в таблице"""

        table = await self.table_repo.get_table_with_write_access(table_id, user_id)
        if not table:
            raise AccessDeniedException("No write access to this table")

        validation_errors = self._validate_row_data_with_schema(
            table.columns_schema, row_data
        )
        if validation_errors:
            raise ValidationException("; ".join(validation_errors))

        row = await self.data_repo.create_table_row(table_id, row_data)

        return TableRowResponse(
            id=row.id,
            table_id=row.table_id,
            row_data=row.row_data,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    #
    async def update_table_row(
        self, table_id: int, row_id: int, user_id: int, row_data: TableRowUpdate
    ) -> Optional[TableRowResponse]:
        """Обновить строку таблицы"""

        table = await self.table_repo.get_table_with_write_access(table_id, user_id)
        if not table:
            raise AccessDeniedException

        validation_errors = self._validate_row_data_with_schema(
            table.columns_schema, row_data
        )
        if validation_errors:
            raise ValidationException("; ".join(validation_errors))

        row = await self.data_repo.update_table_row(table_id, row_id, row_data)
        if not row:
            raise NotFoundException

        return TableRowResponse(
            id=row.id,
            table_id=row.table_id,
            row_data=row.row_data,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    #
    async def delete_table_row(self, table_id: int, row_id: int, user_id: int) -> bool:
        pass

    #     """Удалить строку таблицы"""
    #     # Проверяем доступ на запись
    #     table = await self.table_repo.get_table_with_write_access(table_id, user_id)
    #     if not table:
    #         raise AccessDeniedException("No write access to this table")
    #
    #     # Удаляем строку
    #     success = await self.data_repo.delete_row(table_id, row_id)
    #     if not success:
    #         raise NotFoundException("Row not found")
    #
    #     logger.info(f"User {user_id} deleted row {row_id} from table {table_id}")
    #     return True
    #
    #
