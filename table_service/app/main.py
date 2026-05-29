import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis
from prometheus_fastapi_instrumentator import Instrumentator

from table_service.app.api.endpoints import (
    data_router,
    tables_router,
    search_router,
    permissions_router,
    health_router,
)
from table_service.app.core import (
    init_db,
    app_settings,
    user_event_consumer,
    setup_service_logging,
    close_redis_client,
    close_es_client,
    init_es_index,
)
from table_service.app.exceptions import (
    AccessDeniedException,
    ValidationException,
    NotFoundException,
    CanNotCreateTableException,
    ForbiddenException,
    InvalidFileFormatException,
    InvalidFileMimeTypeException,
    EmptyFileException,
    FileParseException,
    AppException,
    CanNotUpdateTableException,
    PermissionAlreadyExistsException,
    CanNotCreatePermissionException,
)

setup_service_logging()
logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AccessDeniedException)
    async def access_denied_handler(request: Request, exc: AccessDeniedException):
        return JSONResponse(status_code=403, content={"detail": exc.detail})

    @app.exception_handler(ValidationException)
    async def validation_handler(request: Request, exc: ValidationException):
        return JSONResponse(status_code=422, content={"detail": exc.detail})

    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException):
        return JSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(CanNotCreateTableException)
    async def cant_create_handler(request: Request, exc: CanNotCreateTableException):
        return JSONResponse(status_code=500, content={"detail": exc.detail})

    @app.exception_handler(ForbiddenException)
    async def forbidden_handler(request: Request, exc: ForbiddenException):
        return JSONResponse(status_code=403, content={"detail": exc.detail})

    @app.exception_handler(InvalidFileFormatException)
    async def invalid_file_format_handler(
        request: Request, exc: InvalidFileFormatException
    ):
        return JSONResponse(status_code=400, content={"detail": exc.detail})

    @app.exception_handler(InvalidFileMimeTypeException)
    async def invalid_mime_handler(request: Request, exc: InvalidFileMimeTypeException):
        return JSONResponse(status_code=415, content={"detail": exc.detail})

    @app.exception_handler(EmptyFileException)
    async def empty_file_handler(request: Request, exc: EmptyFileException):
        return JSONResponse(status_code=400, content={"detail": exc.detail})

    @app.exception_handler(FileParseException)
    async def file_parse_handler(request: Request, exc: FileParseException):
        return JSONResponse(status_code=400, content={"detail": exc.detail})

    @app.exception_handler(CanNotUpdateTableException)
    async def cannot_update_table_handler(
        request: Request, exc: CanNotUpdateTableException
    ):
        return JSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(PermissionAlreadyExistsException)
    async def permission_exists_handler(
        request: Request, exc: PermissionAlreadyExistsException
    ):
        return JSONResponse(status_code=409, content={"detail": exc.detail})

    @app.exception_handler(CanNotCreatePermissionException)
    async def cant_create_permission_handler(
        request: Request, exc: CanNotCreatePermissionException
    ):
        return JSONResponse(status_code=500, content={"detail": exc.detail})

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(status_code=500, content={"detail": exc.detail})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    """Управление жизненным циклом приложения."""
    await init_db()
    await init_es_index()

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

    await user_event_consumer.close()
    await close_es_client()
    await redis.close()
    await close_redis_client()


def create_app() -> FastAPI:
    """Создание и конфигурация FastAPI приложения."""
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

    register_routers(app)
    register_exception_handlers(app)

    Instrumentator().instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )

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
        (search_router, "/search", "Search"),
        (permissions_router, "/tables/{table_id}/permissions", "Permissions"),
        (health_router, "/health", "Health"),
    ]
    for router, prefix, tag in routers:
        root_router.include_router(router, prefix=prefix, tags=[tag])

    app.include_router(root_router)


app = create_app()
