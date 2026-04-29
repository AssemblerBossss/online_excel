import pytest
from typing import Any

from table_service.app.exceptions import ValidationException
from table_service.app.services.data_validation import DataValidationService
from table_service.app.schemas import TableRowCreate


@pytest.fixture(scope="function")
def service():
    """Инстанс сервиса. Пересоздаётся для каждого теста"""
    return DataValidationService()


@pytest.fixture(scope="function")
def basic_schema() -> list[dict[str, Any]]:
    """Простая схема с разными типами полей."""
    return [
        {"name": "name", "type": "string", "required": True},
        {"name": "age", "type": "number", "required": False},
        {"name": "is_active", "type": "boolean", "required": False},
    ]


@pytest.fixture(scope="function")
def date_schema() -> list[dict[str, Any]]:
    """Схема с полем даты и ограничениями диапазона."""
    return [
        {
            "name": "birth_date",
            "type": "date",
            "required": True,
            "min_date": "1900-01-01",
            "max_date": "2010-12-31",
        }
    ]


@pytest.fixture(scope="function")
def datetime_schema() -> list[dict[str, Any]]:
    """Схема с полем даты и времени."""
    return [
        {
            "name": "created_at",
            "type": "datetime",
            "required": True,
            "min_datetime": "2020-01-01 00:00:00",
            "max_datetime": "2030-12-31 23:59:59",
        }
    ]


@pytest.fixture(scope="function")
def constraint_schema() -> list[dict[str, Any]]:
    """Схема с ограничениями: числовые и строковые."""
    return [
        {"name": "score", "type": "number", "min_value": 0, "max_value": 100},
        {"name": "username", "type": "string", "min_length": 3, "max_length": 20},
        {"name": "status", "type": "string", "enum": ["active", "inactive", "banned"]},
    ]


class TestBuildSchemaDict:

    def test_normal_columns(self):
        """Обычный случай: все колонки имеют name."""
        schema = [
            {"name": "col1", "type": "string"},
            {"name": "col2", "type": "number"},
        ]

        result = DataValidationService._build_schema_dict(schema)

        assert "col1" in result
        assert "col2" in result
        assert result["col1"]["type"] == "string"

    def test_skips_columns_without_name(self):
        """Колонки без 'name' должны игнорироваться."""
        schema = [
            {"type": "string"},
            {"name": "col1", "type": "number"},
        ]

        result = DataValidationService._build_schema_dict(schema)

        assert len(result) == 1
        assert "col1" in result

    def test_empty_schema_returns_empty_dict(self):
        result = DataValidationService._build_schema_dict([])
        assert result == {}


class TestValidateRequiredFields:
    """Тесты проверки обязательных полей."""

    def test_required_field_present(
        self, basic_schema: list[dict[str, Any]], service: DataValidationService
    ):
        row = TableRowCreate(row_data={"name": "Alice", "age": 30})
        errors = service.validate_row_data(
            basic_schema, row_data=row, raise_on_error=False
        )
        assert errors == []

    def test_required_field_missing(
        self, basic_schema: list[dict[str, Any]], service: DataValidationService
    ):
        """Если обязательное поле отсутствует — должна быть ошибка."""
        row = TableRowCreate(
            row_data={"age": 30}
        )  # 'name' — обязательное, но отсутствует
        errors = service.validate_row_data(basic_schema, row, raise_on_error=False)

        assert len(errors) == 1
        assert "name" in errors[0]

    def test_optional_field_missing_is_ok(
        self, basic_schema: list[dict[str, Any]], service: DataValidationService
    ):
        """Необязательное поле может отсутствовать — ошибок нет."""
        row = TableRowCreate(
            row_data={"name": "Bob"}
        )  # age и is_active — необязательные
        errors = service.validate_row_data(basic_schema, row, raise_on_error=False)
        assert errors == []

    def test_raise_on_error_true_raises_exception(
        self, basic_schema: list[dict[str, Any]], service: DataValidationService
    ):
        """При raise_on_error=True должен кидать ValidationException."""
        row = TableRowCreate(row_data={})  # обязательное 'name' отсутствует

        # Тест пройдёт ТОЛЬКО если внутри блока выброшено указанное исключение.
        with pytest.raises(ValidationException):
            service.validate_row_data(basic_schema, row, raise_on_error=True)

    def test_raise_on_error_false_returns_errors(
        self, basic_schema: list[dict[str, Any]], service: DataValidationService
    ):
        """При raise_on_error=False возвращает список ошибок без исключения."""
        row = TableRowCreate(row_data={})
        errors = service.validate_row_data(basic_schema, row, raise_on_error=False)
        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_empty_schema_skips_all_validation(self, service: DataValidationService):
        """Пустая схема — валидация не запускается, ошибок нет."""
        row = TableRowCreate(row_data={"garbage_field": 12345})
        errors = service.validate_row_data([], row, raise_on_error=False)
        assert errors == []


class TestValidateDataTypes:
    """Тесты проверки типов данных."""

    @pytest.mark.parametrize(
        "value,should_fail",
        [
            ("hello", False),  # строка — ок
            (123, True),  # int — ошибка
            (3.14, True),  # float — ошибка
            (True, True),  # bool — ошибка (bool это subclass int в Python!)
            (None, False),  # None пропускается
            ("", False),  # пустая строка пропускается
        ],
    )
    def test_string_type(
        self,
        service: DataValidationService,
        value: Any,
        should_fail: bool,
    ) -> None:
        schema = [{"name": "field", "type": "string"}]
        row = TableRowCreate(row_data={"field": value})
        errors = service.validate_row_data(
            table_columns_schema=schema, row_data=row, raise_on_error=False
        )
        if should_fail:
            assert any(
                "field" in e for e in errors
            ), f"Ожидалась ошибка для value={value!r}"
        else:
            assert errors == [], f"Не ожидалась ошибка для value={value!r}"

    @pytest.mark.parametrize(
        "value,should_fail",
        [
            (42, False),  # int — ок
            (3.14, False),  # float — ок
            ("42", False),  # строка с числом — ок
            ("3.14", False),  # строка с float — ок
            ("abc", True),  # не число — ошибка
            ([], True),  # список — ошибка
        ],
    )
    def test_number_type(
        self, service: DataValidationService, value: Any, should_fail: bool
    ) -> None:
        schema = [{"name": "amount", "type": "number"}]
        row = TableRowCreate(row_data={"amount": value})
        errors = service.validate_row_data(schema, row, raise_on_error=False)
        if should_fail:
            assert any("amount" in e for e in errors)
        else:
            assert errors == []

    @pytest.mark.parametrize(
        "value,should_fail",
        [
            (True, False),
            (False, False),
            ("true", True),  # строка не считается bool
            (1, True),  # int не считается bool (хотя bool subclass int!)
            (0, True),
        ],
    )
    def test_boolean_type(
        self, service: DataValidationService, value: Any, should_fail: bool
    ) -> None:
        schema = [{"name": "flag", "type": "boolean"}]
        row = TableRowCreate(row_data={"flag": value})
        errors = service.validate_row_data(
            table_columns_schema=schema, row_data=row, raise_on_error=False
        )
        if should_fail:
            assert any("flag" in e for e in errors)
        else:
            assert errors == []

    def test_unknown_type_in_schema_is_ignored(
        self, service: DataValidationService
    ) -> None:
        """Если в схеме тип которого нет в коде — просто пропускаем без ошибок."""
        schema = [{"name": "data", "type": "json"}]
        row = TableRowCreate(row_data={"data": {"nested": True}})
        errors = service.validate_row_data(schema, row, raise_on_error=False)
        assert errors == []

    def test_field_not_in_schema_is_ignored(
        self, service: DataValidationService
    ) -> None:
        """Поля, которых нет в схеме, молча игнорируются."""
        schema = [{"name": "name", "type": "string"}]
        row = TableRowCreate(row_data={"name": "Alice", "extra_field": 999})
        errors = service.validate_row_data(schema, row, raise_on_error=False)
        assert errors == []


class TestDateValidation:
    """Тесты валидации дат."""

    @pytest.mark.parametrize(
        "date_value",
        [
            "2000-06-15",  # ISO формат
            "15.06.2000",  # российский формат
            "15/06/2000",  # европейский формат
            "2000.06.15",  # ещё один вариант
        ],
    )
    def test_valid_date_formats(
        self,
        service: DataValidationService,
        date_schema: list[dict[str, Any]],
        date_value: Any,
    ) -> None:
        """Все поддерживаемые форматы дат должны проходить валидацию."""
        row = TableRowCreate(row_data={"birth_date": date_value})
        errors = service.validate_row_data(date_schema, row, raise_on_error=False)
        assert errors == [], f"Неожиданная ошибка для даты: {date_value}"

    @pytest.mark.parametrize(
        "date_value",
        [
            "2000/15/06",  # день и месяц перепутаны
            "15-06-2000",  # неправильный разделитель
            "not-a-date",
            "2000-13-01",  # несуществующий месяц
        ],
    )
    def test_invalid_date_formats(
        self,
        service: DataValidationService,
        date_schema: list[dict[str, Any]],
        date_value: str,
    ) -> None:
        row = TableRowCreate(row_data={"birth_date": date_value})
        errors = service.validate_row_data(date_schema, row, raise_on_error=False)
        assert len(errors) > 0, f"Должна быть ошибка для: {date_value}"

    def test_date_before_min_date(
        self, service: DataValidationService, date_schema: list[dict[str, Any]]
    ) -> None:
        """Дата раньше min_date должна давать ошибку."""
        row = TableRowCreate(row_data={"birth_date": "1800-01-01"})
        errors = service.validate_row_data(date_schema, row, raise_on_error=False)
        assert any("раньше" in e for e in errors)

    def test_date_after_max_date(
        self, service: DataValidationService, date_schema: list[dict[str, Any]]
    ) -> None:
        """Дата позже max_date должна давать ошибку."""
        row = TableRowCreate(row_data={"birth_date": "2025-01-01"})
        errors = service.validate_row_data(date_schema, row, raise_on_error=False)
        assert any("позже" in e for e in errors)

    def test_date_on_boundary_min(
        self, service: DataValidationService, date_schema: list[dict[str, Any]]
    ) -> None:
        """Граничное значение min_date должно проходить."""
        row = TableRowCreate(row_data={"birth_date": "1900-01-01"})  # ровно min_date
        errors = service.validate_row_data(date_schema, row, raise_on_error=False)
        assert errors == []

    def test_date_on_boundary_max(
        self, service: DataValidationService, date_schema: list[dict[str, Any]]
    ) -> None:
        """Граничное значение max_date должно проходить."""
        row = TableRowCreate(row_data={"birth_date": "2010-12-31"})  # ровно max_date
        errors = service.validate_row_data(date_schema, row, raise_on_error=False)
        assert errors == []

    def test_date_field_not_a_string(
        self, service: DataValidationService, date_schema: list[dict[str, Any]]
    ) -> None:
        """Если передать не строку в поле даты — ошибка типа."""
        row = TableRowCreate(row_data={"birth_date": 20001231})
        errors = service.validate_row_data(date_schema, row, raise_on_error=False)
        assert len(errors) > 0


class TestConstraintValidation:
    """
    Тесты валидации ограничений.

    💡 JUNIOR NOTE: Граничные значения (boundary values) — классика тестирования.
    Всегда проверяй: min-1, min, min+1, max-1, max, max+1.
    """

    def test_number_within_range(
        self, service: DataValidationService, constraint_schema: list[dict[str, Any]]
    ) -> None:
        row = TableRowCreate(
            row_data={"score": 50, "username": "alice", "status": "active"}
        )
        errors = service.validate_row_data(constraint_schema, row, raise_on_error=False)
        assert errors == []

    def test_number_below_min(
        self, service: DataValidationService, constraint_schema: list[dict[str, Any]]
    ) -> None:
        row = TableRowCreate(row_data={"score": -1})
        errors = service.validate_row_data(constraint_schema, row, raise_on_error=False)
        assert any("score" in e and "меньше" in e for e in errors)

    def test_number_above_max(
        self, service: DataValidationService, constraint_schema: list[dict[str, Any]]
    ):
        row = TableRowCreate(row_data={"score": 101})
        errors = service.validate_row_data(constraint_schema, row, raise_on_error=False)
        assert any("score" in e and "больше" in e for e in errors)

    @pytest.mark.parametrize("score", [0, 50, 100])
    def test_number_on_boundaries(
        self,
        service: DataValidationService,
        constraint_schema: list[dict[str, Any]],
        score,
    ) -> None:
        """Граничные значения 0 и 100 должны проходить."""
        row = TableRowCreate(row_data={"score": score})
        errors = service.validate_row_data(constraint_schema, row, raise_on_error=False)
        assert errors == [], f"score={score} должен быть валидным"

    def test_string_too_short(
        self, service: DataValidationService, constraint_schema: list[dict[str, Any]]
    ) -> None:
        row = TableRowCreate(row_data={"username": "ab"})  # min_length=3
        errors = service.validate_row_data(constraint_schema, row, raise_on_error=False)
        assert any("username" in e for e in errors)

    def test_string_too_long(
        self, service: DataValidationService, constraint_schema: list[dict[str, Any]]
    ) -> None:
        row = TableRowCreate(row_data={"username": "a" * 21})  # max_length=20
        errors = service.validate_row_data(constraint_schema, row, raise_on_error=False)
        assert any("username" in e for e in errors)

    @pytest.mark.parametrize("status", ["active", "inactive", "banned"])
    def test_valid_enum_values(
        self, service, constraint_schema: list[dict[str, Any]], status
    ) -> None:
        row = TableRowCreate(row_data={"status": status})
        errors = service.validate_row_data(constraint_schema, row, raise_on_error=False)
        assert errors == []

    def test_invalid_enum_value(
        self, service: DataValidationService, constraint_schema: list[dict[str, Any]]
    ) -> None:
        row = TableRowCreate(row_data={"status": "deleted"})
        errors = service.validate_row_data(constraint_schema, row, raise_on_error=False)
        assert any("status" in e for e in errors)

    def test_multiple_errors_returned_at_once(
        self, service: DataValidationService, constraint_schema: list[dict[str, Any]]
    ):
        """Все ошибки должны накапливаться, а не останавливаться на первой."""
        row = TableRowCreate(
            row_data={
                "score": 999,  # слишком большое
                "username": "x",  # слишком короткое
                "status": "unknown",  # не из enum
            }
        )
        errors = service.validate_row_data(constraint_schema, row, raise_on_error=False)
        assert len(errors) == 3
