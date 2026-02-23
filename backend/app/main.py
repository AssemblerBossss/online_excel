from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.app.api.endpoints import (
    auth_router,
    data_router,
    tables_router,
    users_router,
)
from backend.app.core.settings import app_settings
from backend.app.middleware import FileSizeLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    """Управление жизненным циклом приложения."""
    logger.info("Инициализация приложения...")

    yield

    logger.info("Завершение работы приложения...")


def create_app() -> FastAPI:
    """
    Создание и конфигурация FastAPI приложения.

    Returns:
        Сконфигурированное приложение FastAPI
    """
    app = FastAPI(
        title="Стартовая сборка FastAPI",
        description=(
            "Стартовая сборка с интегрированной SQLAlchemy 2 для разработки FastAPI приложений с продвинутой "
            "архитектурой, включающей авторизацию, аутентификацию и управление ролями пользователей.\n\n"
            "**Автор проекта**: Яковенко Алексей\n"
            "**Telegram**: https://t.me/PythonPathMaster"
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        FileSizeLimitMiddleware, max_file_size=app_settings.MAX_FILE_SIZE_BYTES
    )

    # Регистрация роутеров
    register_routers(app)

    return app


def register_routers(app: FastAPI) -> None:
    """Регистрация роутеров приложения."""

    # Корневой роутер с префиксом /api
    root_router = APIRouter(prefix="/api")

    @root_router.get("/", tags=["root"])
    async def home_page():
        return {
            "message": "Table Service API",
            "version": "1.0.0",
            "docs": "/api/docs",
        }

    # Подключение дочерних роутеров
    routers = [
        (auth_router, "/auth", "Auth"),
        (data_router, "/data", "Data"),
        (users_router, "/users", "Users"),
        (tables_router, "/tables", "Tables"),
    ]

    for router, prefix, tag in routers:
        root_router.include_router(router, prefix=prefix, tags=[tag])
        logger.debug(f"Зарегистрирован роутер {tag} с префиксом /api{prefix}")

    app.include_router(root_router)


app = create_app()
