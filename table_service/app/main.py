from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from table_service.app.api.endpoints import (
    data_router,
    tables_router,
)
from table_service.app.core.settings import app_settings
from table_service.app.middleware import FileSizeLimitMiddleware


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

    app.add_middleware(
        FileSizeLimitMiddleware, max_file_size=app_settings.MAX_FILE_SIZE_BYTES
    )

    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Монтирование статических файлов
    # app.mount(
    #     '/static',
    #     StaticFiles(directory='app/static'),
    #     name='static'
    # )

    # Регистрация роутеров
    register_routers(app)

    return app


def register_routers(app: FastAPI) -> None:
    """Регистрация роутеров приложения."""
    # Корневой роутер
    API_PREFIX = "/api"
    root_router = APIRouter(prefix=API_PREFIX, tags=["root"])

    @root_router.get("/", tags=["root"])
    def home_page():
        return {
            "message": "Добро пожаловать! Проект создан для сообщества 'Легкий путь в Python'.",
            "community": "https://t.me/PythonPathMaster",
            "author": "Яковенко Алексей",
        }

    # Подключение дочерних роутеров к корневому с префиксом /api
    root_router.include_router(data_router, prefix="/data", tags=["Data"])
    root_router.include_router(tables_router, prefix="/tables", tags=["Tables"])

    # Регистрируем корневой роутер в приложении
    app.include_router(root_router)


app = create_app()
