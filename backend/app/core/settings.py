from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Literal

LOG_FORMAT_DEFAULT = (
    "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
)


class LoggingConfig(BaseModel):
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    log_format: str = LOG_FORMAT_DEFAULT


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
    logging: LoggingConfig = LoggingConfig()

    DB_HOST: str = "0.0.0.0"
    DB_PORT: int = 7777
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "pomodoro"
    DB_NAME: str = "pomodoro"
    DB_DRIVER: str = "postgresql+asyncpg"

    CACHE_HOST: str = "0.0.0.0"
    CACHE_PORT: int = 14000
    CACHE_DB: int = 0

    JWT_SECRET: str = "secret"
    JWT_ALGORITHM: str = "HS256"

    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    GOOGLE_TOKEN_URL: str = "https://accounts.google.com/o/oauth2/token"

    @property
    def db_url(self) -> str:
        return f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def google_redirect_url(self) -> str:
        return f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={self.GOOGLE_CLIENT_ID}&redirect_uri={self.GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"


app_settings = Settings()
