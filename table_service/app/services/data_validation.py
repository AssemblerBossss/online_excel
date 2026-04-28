import logging
from datetime import datetime
from typing import Any

from table_service.app.schemas import TableRowCreate, TableRowUpdate
from table_service.app.exceptions import ValidationException

logger = logging.getLogger(__name__)


class DataValidationService:
    """Service for validating row data against table column schema."""

    def __init__(self):
        """Initialize validation service."""
        pass

    def validate_row_data(
        self,
        table_columns_schema: list[dict[str, Any]],
        row_data: TableRowCreate | TableRowUpdate,
        raise_on_error: bool = True,
    ) -> list[str]:
        """
        Проверить данные строки на соответствие схеме столбцов таблицы.

        Args:
            table_columns_schema: Список схем столбцов таблицы
            row_data: Данные строки для проверки
            raise_on_error: Если True, при ошибках валидации вызывается исключение ValidationException

        Returns:
            Список сообщений об ошибках валидации (пустой список, если ошибок нет)

        Raises:
            ValidationException: Если raise_on_error=True и валидация не пройдена
        """

        errors = []

        if not table_columns_schema:
            return errors

        schema_dict = self._build_schema_dict(table_columns_schema)

        # Check required fields
        errors.extend(self._validate_required_fields(schema_dict, row_data.row_data))

        # Validate data types and transform if needed
        errors.extend(self._validate_data_types(schema_dict, row_data.row_data))

        # Validate value constraints
        errors.extend(self._validate_constraints(schema_dict, row_data.row_data))

        if errors and raise_on_error:
            raise ValidationException("; ".join(errors))

        return errors

    @staticmethod
    def _build_schema_dict(table_columns_schema: list[dict[str, Any]]):
        """Создать словарь схемы, индексированный по имени столбца."""
        return {
            col_schema.get("name"): col_schema
            for col_schema in table_columns_schema
            if col_schema.get("name")
        }

    @staticmethod
    def _validate_required_fields(
        schema_dict: dict[str, dict], row_data: dict[str, Any]
    ):
        """Проверить, что все обязательные поля присутствуют."""
        errors = []
        for col_name, col_schema in schema_dict.items():
            if col_schema.get("required", False) and col_name not in row_data:
                errors.append(f"Обязательное поле '{col_name}' отсутствует")
        return errors

    def _validate_data_types(
        self, schema_dict: dict[str, dict], row_data: dict[str, Any]
    ) -> list[str]:
        """Проверить и опционально преобразовать типы данных."""
        errors = []

        for col_name, value in row_data.items():
            if col_name not in schema_dict or value == "" or value is None:
                continue

            col_schema = schema_dict[col_name]
            expected_type = col_schema.get("type", "string")

            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Поле {col_name} должно быть строкой")

            elif expected_type == "number":
                error = self._validate_number_field(value=value, col_name=col_name)
                if error:
                    errors.append(error)

            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Поле {col_name} должно быть булевым")

            elif expected_type == "date":
                date_error = self._validate_date_field(
                    value=value, col_name=col_name, col_schema=col_schema
                )
                if date_error:
                    errors.append(date_error)

            elif expected_type == "datetime":
                datetime_error = self._validate_datetime_field(
                    value=value, col_name=col_name, col_schema=col_schema
                )
                if datetime_error:
                    errors.append(datetime_error)

        return errors

    @staticmethod
    def _validate_number_field(value: Any, col_name: str) -> str | None:
        """Проверить и преобразовать числовое поле."""
        if isinstance(value, str):
            try:
                # Convert string to number (int or float)
                if "." in value:
                    return None  # Will be converted to float later
                else:
                    return None  # Will be converted to int later
            except ValueError:
                return f"Поле {col_name} должно быть числом"
        elif not isinstance(value, (int, float)):
            return f"Поле {col_name} должно быть числом"
        return None

    @staticmethod
    def _validate_date_field(value: Any, col_name: str, col_schema: dict) -> str | None:
        """Проверить поле даты с опциональным диапазоном дат."""
        if not isinstance(value, str):
            return f"Поле '{col_name}' должно быть строкой с датой"

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

        if "min_date" in col_schema:
            min_date = datetime.strptime(col_schema["min_date"], "%Y-%m-%d").date()
            if parsed_date < min_date:
                return f"Дата в поле '{col_name}' не может быть раньше {col_schema['min_date']}"

        if "max_date" in col_schema:
            max_date = datetime.strptime(col_schema["max_date"], "%Y-%m-%d").date()
            if parsed_date > max_date:
                return f"Дата в поле '{col_name}' не может быть позже {col_schema['max_date']}"

        return None

    @staticmethod
    def _validate_datetime_field(
        value: Any, col_name: str, col_schema: dict
    ) -> str | None:
        """Проверить поле даты и времени с опциональным диапазоном."""
        if not isinstance(value, str):
            return f"Поле '{col_name}' должно быть строкой с датой и временем"

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
            min_dt = datetime.strptime(col_schema["min_datetime"], "%Y-%m-%d %H:%M:%S")
            if parsed_datetime < min_dt:
                return f"Дата/время в поле '{col_name}' не может быть раньше {col_schema['min_datetime']}"

        if "max_datetime" in col_schema:
            max_dt = datetime.strptime(col_schema["max_datetime"], "%Y-%m-%d %H:%M:%S")
            if parsed_datetime > max_dt:
                return f"Дата/время в поле '{col_name}' не может быть позже {col_schema['max_datetime']}"

        return None

    @staticmethod
    def _validate_constraints(
        schema_dict: dict[str, dict], row_data: dict[str, Any]
    ) -> list[str]:
        """Проверить ограничения значения (мин/макс, длина, перечисление)."""
        errors = []

        for col_name, value in row_data.items():
            if col_name not in schema_dict or value == "" or value is None:
                continue

            col_schema = schema_dict[col_name]

            # Numeric constraints
            if isinstance(value, (int, float)):
                if "min_value" in col_schema and value < col_schema["min_value"]:
                    errors.append(
                        f"Значение поля '{col_name}' не может быть меньше {col_schema['min_value']}"
                    )
                if "max_value" in col_schema and value > col_schema["max_value"]:
                    errors.append(
                        f"Значение поля '{col_name}' не может быть больше {col_schema['max_value']}"
                    )

            # String length constraints
            if isinstance(value, str):
                if "min_length" in col_schema and len(value) < col_schema["min_length"]:
                    errors.append(
                        f"Длина поля '{col_name}' не может быть меньше {col_schema['min_length']} символов"
                    )
                if "max_length" in col_schema and len(value) > col_schema["max_length"]:
                    errors.append(
                        f"Длина поля '{col_name}' не может быть больше {col_schema['max_length']} символов"
                    )

            # Enum constraints
            if "enum" in col_schema and value not in col_schema["enum"]:
                errors.append(
                    f"Значение поля '{col_name}' должно быть одним из: {', '.join(map(str, col_schema['enum']))}"
                )

        return errors

    async def validate_batch(
        self,
        table_columns_schema: list[dict[str, Any]],
        rows_data: list[TableRowCreate | TableRowUpdate],
        stop_on_first_error: bool = False,
    ) -> dict[int, list[str]]:
        """
        Валидировать несколько строк в пакетном режиме.

        Args:
            table_columns_schema: Схема столбцов таблицы
            rows_data: Список строк для валидации
            stop_on_first_error: Если True, останавливает валидацию при первой ошибке

        Returns:
            Словарь, отображающий индекс строки в список ошибок
        """
        errors_by_row = {}
        for idx, row in enumerate(rows_data):
            errors = self.validate_row_data(
                table_columns_schema=table_columns_schema,
                row_data=row,
                raise_on_error=stop_on_first_error,
            )

            if errors:
                errors_by_row[idx] = errors
                if stop_on_first_error:
                    break
        return errors_by_row
