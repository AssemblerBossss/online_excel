from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Auth Service Configuration"""

    PROJECT_NAME: str = "Auth Service"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
