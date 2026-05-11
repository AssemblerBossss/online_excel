import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded

from api_gateway.app.config import settings
from api_gateway.app.middleware import (
    JWTAuthMiddleware,
    RequestLoggingMiddleware,
    RateLimiterMiddleware,
)
from api_gateway.app.utils import init_http_client, close_http_client
from api_gateway.app.routers import health_router, proxy_router
from api_gateway.app.core import setup_logging
from api_gateway.app.middleware.rate_limit import limiter, custom_rate_limit_handler

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Initializing HTTP client...")
    await init_http_client()

    yield

    logging.info("Closing HTTP client...")
    await close_http_client()


# Создание приложения
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    description="API Gateway for Online Excel Microservices",
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

# CORS Middleware (должен быть первым)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimiterMiddleware, limiter=limiter)
app.add_middleware(JWTAuthMiddleware)

# Роутеры
app.include_router(health_router, tags=["health"])
app.include_router(proxy_router, tags=["proxy"])
# app.include_router(auth_proxy.router, prefix="/api/v1", tags=["auth-proxy"])
# app.include_router(tables_proxy.router, prefix="/api/v1", tags=["tables-proxy"])


@app.get("/")
async def root():
    return {"service": "API Gateway", "version": settings.VERSION, "status": "running"}
