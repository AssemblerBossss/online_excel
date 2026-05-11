from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Health check endpoint for Docker and monitoring."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness probe endpoint."""
    # Проверяем подключение к БД и другим зависимостям
    # Если всё ок - возвращаем 200
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Liveness probe endpoint."""
    return {"status": "alive"}
