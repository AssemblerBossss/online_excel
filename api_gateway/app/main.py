import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from slowapi import _rate_limit_exceeded_handler
# from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware import JWTAuthMiddleware
from app.middleware import RequestLoggingMiddleware

# from api_gateway.app.middleware.rate_limit import limiter
from app.routers import health_router, proxy_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Создание приложения
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API Gateway for Online Excel Microservices",
)

# Rate Limiting
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.add_middleware(JWTAuthMiddleware)

# Роутеры
app.include_router(health_router, tags=["health"])
app.include_router(proxy_router, prefix="/api/v1", tags=["proxy"])
# app.include_router(auth_proxy.router, prefix="/api/v1", tags=["auth-proxy"])
# app.include_router(tables_proxy.router, prefix="/api/v1", tags=["tables-proxy"])


@app.get("/")
async def root():
    return {"service": "API Gateway", "version": settings.VERSION, "status": "running"}
