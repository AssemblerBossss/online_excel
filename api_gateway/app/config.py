from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "API Gateway"
    VERSION: str = "1.0.0"

    # JWT Settings
    JWT_SECRET_KEY: str = "secret"
    JWT_ALGORITHM: str = "HS256"

    # Backend Services URLs
    AUTH_SERVICE_URL: str = "http://auth_service:8001"
    MAIN_SERVICE_URL: str = "http://table_service:8000"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
