from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Auth Service Configuration"""

    PROJECT_NAME: str = "Auth Service"
    VERSION: str = "1.0.0"
    API_STR: str = "/api"

    DB_HOST: str = "auth_db"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "auth_db"
    DB_DRIVER: str = "postgresql+asyncpg"

    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def RABBITMQ_URL(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


auth_service_settings = Settings()
