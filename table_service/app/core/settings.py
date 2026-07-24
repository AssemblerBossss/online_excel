from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict

LOG_FORMAT_DEFAULT = (
    "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
)


class UvicornConfig(BaseSettings):
    APP_PORT: int = 8080
    APP_HOST: str = "0.0.0.0"


class GunicornConfig(BaseSettings):
    APP_PORT: int = 8080
    APP_HOST: str = "0.0.0.0"
    WORKERS: int = 4
    TIMEOUT: int = 900


class Settings(BaseSettings):
    gunicorn: GunicornConfig = GunicornConfig()
    uvicorn: UvicornConfig = UvicornConfig()

    DB_HOST: str = "online_excel_db"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "online_excel"
    DB_NAME: str = "online_excel"
    DB_DRIVER: str = "postgresql+asyncpg"

    CACHE_HOST: str = "redis"
    CACHE_PORT: int = 6379
    CACHE_DB: int = 0

    ES_HOST: str = "elasticsearch"
    ES_PORT: int = 9200

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

    MAX_FILE_SIZE_MB: int = 10  # Максимальный размер файла в MB
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB в байтах

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_PUBLIC_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_EXPORT_BUCKET: str = "exports"
    MINIO_SECURE: bool = False

    @cached_property
    def DATABASE_URL(self) -> str:
        return f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @cached_property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    model_config = SettingsConfigDict(
        env_file=[".env.development", "local.env"],
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_prefix="EXCEL_APP__",
        extra="ignore",
    )


app_settings = Settings()
