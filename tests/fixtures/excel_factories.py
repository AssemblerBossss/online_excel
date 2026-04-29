import pytest
from io import BytesIO
from unittest.mock import MagicMock
import pandas as pd
import numpy as np
from fastapi import UploadFile


def create_excel_file(filename: str, data: pd.DataFrame) -> MagicMock:
    """Фабрика для создания мока UploadFile с Excel данными"""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        data.to_excel(writer, index=False)
    buffer.seek(0)

    file = MagicMock(spec=UploadFile)
    file.filename = filename
    file.content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    file.file = buffer
    return file


@pytest.fixture
def valid_excel_file():
    """Создает реальный Excel файл с данными"""
    df = pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Charlie"],
            "Age": [25, 30, 35],
            "Email": ["alice@example.com", "bob@example.com", "charlie@example.com"],
            "Active": [True, False, True],
        }
    )
    return create_excel_file("test_data.xlsx", df)


@pytest.fixture
def excel_file_with_empty_sheet():
    """Excel файл с пустым листом"""
    df = pd.DataFrame()
    return create_excel_file("empty.xlsx", df)


@pytest.fixture
def excel_file_with_mixed_types():
    """Excel файл со смешанными типами данных"""
    df = pd.DataFrame(
        {
            "ID": [1, 2, 3, 4],
            "Name": ["Product A", "Product B", None, "Product D"],
            "Price": [10.99, 25.50, np.nan, 45.00],
            "InStock": [True, False, True, None],
            "Tags": ["electronics", "home", "toys", "books"],
        }
    )
    return create_excel_file("mixed_types.xlsx", df)


@pytest.fixture
def excel_file_large():
    """Большой Excel файл для нагрузочных тестов"""
    df = pd.DataFrame({f"col_{i}": range(1000) for i in range(50)})
    return create_excel_file("large.xlsx", df)


@pytest.fixture
def excel_file_special_chars():
    """Excel с спецсимволами и эмодзи"""
    df = pd.DataFrame(
        {
            "Русское название": ["Привет", "Мир"],
            "Emoji 🎉": ["😀", "🎈"],
            "Special!@#": ["value1", "value2"],
        }
    )
    return create_excel_file("special.xlsx", df)
