import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis

from table_service.app.api.endpoints import (
    data_router,
    tables_router,
)
from table_service.app.core import (
    init_db,
    app_settings,
    user_event_consumer,
    user_validator_instance,
    setup_service_logging,
)


setup_service_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    """Управление жизненным циклом приложения."""
    await user_validator_instance.connect()
    await init_db()

    redis = Redis(
        host=app_settings.CACHE_HOST,
        port=app_settings.CACHE_PORT,
        db=app_settings.CACHE_DB,
        encoding="utf8",
        decode_responses=False,
    )
    FastAPICache.init(RedisBackend(redis), prefix="table_service")

    await user_event_consumer.connect()
    logger.info("UserEventConsumer started")

    yield
    await user_validator_instance.close()
    await user_event_consumer.close()
    await redis.close()


def create_app() -> FastAPI:
    """
    Создание и конфигурация FastAPI приложения.

    Returns:
        Сконфигурированное приложение FastAPI
    """
    app = FastAPI(
        title="Table Service",
        description="Сервис для управления таблицами и данными",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Регистрация роутеров
    register_routers(app)

    return app


def register_routers(app: FastAPI) -> None:
    """Регистрация роутеров приложения."""
    # Корневой роутер
    root_router = APIRouter()

    @root_router.get("/", tags=["root"])
    async def home_page():
        return {
            "name": "Table Service",
            "version": "1.0.0",
            "description": "Сервис для управления таблицами и данными",
            "endpoints": {
                "tables": "/api/tables",
                "data": "/api/data",
                "docs": "/api/docs",
            },
        }

    # Подключение дочерних роутеров
    routers = [
        (data_router, "/data", "Data"),
        (tables_router, "/tables", "Tables"),
    ]
    for router, prefix, tag in routers:
        root_router.include_router(router, prefix=prefix, tags=[tag])

    app.include_router(root_router)


app = create_app()
