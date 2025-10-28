from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from backend.app.api.endpoints import auth_router, data_router, tables_router
from backend.app.utils import init_admin_user
from backend.app.core import AsyncSessionFactory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    """Управление жизненным циклом приложения."""
    logger.info("Инициализация приложения...")

    try:
        async with AsyncSessionFactory() as session:
            await init_admin_user(session)
            logger.info("Admin user initialization completed")
    except Exception as e:
        logger.error(f"Failed to initialize admin user: {e}")

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
    root_router = APIRouter()

    @root_router.get("/", tags=["root"])
    def home_page():
        return {
            "message": "Добро пожаловать! Проект создан для сообщества 'Легкий путь в Python'.",
            "community": "https://t.me/PythonPathMaster",
            "author": "Яковенко Алексей",
        }

    # Подключение роутеров
    app.include_router(root_router, tags=["root"])
    app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    app.include_router(data_router, prefix="/data", tags=["Data"])
    app.include_router(tables_router, prefix="/tables", tags=["Tables"])


app = create_app()
