from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
async def health_check():
    """
    Простой health check endpoint.
    Возвращает статус сервиса и базовую информацию.
    """
    return {
        "status": "healthy",
        "service": "Table Service Health Check",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
    }
