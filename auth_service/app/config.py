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

    JWT_SECRET_KEY: str = "secret"  # не используется при RS256
    JWT_ALGORITHM: str = "RS256"
    JWT_PRIVATE_KEY_PATH: str = "/run/secrets/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "/run/secrets/jwt_public.pem"

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1
    RATE_LIMIT_REGISTER: str = "3/minute"
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REFRESH: str = "10/minute"
    RATE_LIMIT_LOGOUT: str = "20/minute"

    # MinIO / S3 storage
    MINIO_ENDPOINT: str = "minio:9000"  # адрес для SDK внутри сети
    MINIO_PUBLIC_URL: str = "http://localhost:9000"  # база для ссылок в браузере
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "avatars"
    MINIO_SECURE: bool = False

    MAX_AVATAR_SIZE: int = 5 * 1024 * 1024
    ALLOWED_AVATAR_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}

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

    @property
    def REDIS_URL(self) -> str:
        """Redis URL для slowapi (с async+ префиксом)"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


auth_service_settings = Settings()
