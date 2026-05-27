import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


from auth_service.app.config import auth_service_settings
from auth_service.app.utils import avatar_storage
from auth_service.app.сore import init_db, setup_service_logging, limiter
from auth_service.app.routers import auth_router, user_router, health_router
from auth_service.app.events import event_publisher
from auth_service.app.exceptions import AppException


setup_service_logging()
logger = logging.getLogger(__name__)


async def custom_rate_limit_handler(
    request: Request, exc: RateLimitExceeded
) -> Response:
    """Кастомный обработчик превышения лимита запросов."""
    return _rate_limit_exceeded_handler(request, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting Auth Service...")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

    await init_db()
    logger.info("✅ Database initialized")

    await event_publisher.connect()
    logger.info("✅ Event publisher connected")

    await avatar_storage.ensure_avatar_bucket()
    logger.info("✅  MinIO bucket ready")

    yield

    logger.info("🛑 Shutting down Auth Service...")
    await event_publisher.disconnect()


app = FastAPI(
    title=auth_service_settings.PROJECT_NAME,
    version=auth_service_settings.VERSION,
    lifespan=lifespan,
    # redirect_slashes=False,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажи конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(health_router, prefix="/health", tags=["health"])


# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Обработчик кастомных доменных исключений"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
