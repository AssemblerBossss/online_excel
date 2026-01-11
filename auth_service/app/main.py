from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from auth_service.app.config import auth_service_settings
from auth_service.app.database import init_db
from auth_service.app.routers import auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("🚀 Starting Auth Service...")

    # Инициализация БД
    await init_db()
    logger.info("✅ Database initialized")

    yield

    logger.info("🛑 Shutting down Auth Service...")


app = FastAPI(
    title=auth_service_settings.PROJECT_NAME,
    version=auth_service_settings.VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажи конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/api", tags=["auth"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": auth_service_settings.PROJECT_NAME,
        "version": auth_service_settings.VERSION,
    }
