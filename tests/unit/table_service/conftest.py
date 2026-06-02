import pytest
from unittest.mock import AsyncMock, MagicMock
from contextlib import contextmanager, asynccontextmanager
from tests.fixtures.excel_factories import (  # noqa: F401
    valid_excel_file,
    excel_file_with_empty_sheet,
    excel_file_with_mixed_types,
    excel_file_large,
    excel_file_special_chars,
)
from table_service.app.models import DataTable
from table_service.app.services.table import TableService


@pytest.fixture
def mock_uow(mock_table_repo, mock_data_repo, mock_permission_service):
    uow = MagicMock()
    uow.tables = mock_table_repo  # uow_session.tables -> тот же мок
    uow.data = mock_data_repo  # uow_session.data
    uow.permissions = AsyncMock()
    uow.users = AsyncMock()

    @asynccontextmanager
    async def _start():
        yield uow  # поддерживает и вложенный start()

    uow.start = _start
    return uow


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

    monkeypatch.setattr(
        "table_service.app.core.rabbitmq.get_user_validator", mock_get_user_validator
    )
    monkeypatch.setattr(
        "table_service.app.core.get_user_validator", mock_get_user_validator
    )


# Моки для репозиториев
@pytest.fixture
def mock_table_repo():
    repo = AsyncMock()
    repo.get_all_tables = AsyncMock()
    repo.get_table_by_id = AsyncMock()
    repo.create_table = AsyncMock()
    repo.update_table = AsyncMock()
    repo.delete_table = AsyncMock()
    return repo


@pytest.fixture
def mock_data_repo():
    repo = AsyncMock()
    repo.bulk_create_table_row = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_permission_service():
    service = AsyncMock()
    service.check_read_access = AsyncMock(return_value=True)
    service.check_write_access = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_search_service():
    service = AsyncMock()
    service.index_table = AsyncMock()
    service.update_table = AsyncMock()
    service.delete_from_index = AsyncMock()
    return service


@pytest.fixture
def real_data_table() -> DataTable:
    return DataTable(
        id=1,
        name="Test Table",
        description="Test description",
        is_public=False,
        columns_schema=[{"name": "col1", "type": "string", "required": False}],
        created_by_id=100,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


@pytest.fixture
def service(mock_table_repo, mock_data_repo, mock_permission_service) -> TableService:
    return TableService(
        permission_service=mock_permission_service,
    )


@pytest.fixture
def service_with_search(
    mock_table_repo, mock_data_repo, mock_permission_service, mock_search_service
) -> TableService:
    return TableService(
        permission_service=mock_permission_service,
        search_service=mock_search_service,
    )
