import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DB_URL: str = "postgresql+asyncpg://postgres:password@0.0.0.0:5000/excel_online"
    SECRET_KEY: str = "dfgdfgdfgdfg"
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=f"{BASE_DIR}/.env.example")


# Получаем параметры для загрузки переменных среды
settings = Settings()
database_url = settings.DB_URL
