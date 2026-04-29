import pytest
from unittest.mock import AsyncMock, MagicMock
from contextlib import contextmanager


@pytest.fixture(autouse=True)
def mock_user_validator(monkeypatch):
    """Мокает get_user_validator() для всех unit-тестов.

    Интеграционные тесты могут переопределить этот fixture,
    чтобы использовать реальный валидатор или другую заглушку.
    """
    mock_instance = MagicMock()
    mock_instance.check_exists = AsyncMock(return_value=True)

    @contextmanager
    def mock_get_user_validator():
        yield mock_instance

    monkeypatch.setattr("table_service.app.core.rabbitmq.get_user_validator", mock_get_user_validator)
    monkeypatch.setattr("table_service.app.core.get_user_validator", mock_get_user_validator)