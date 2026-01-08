import httpx
from fastapi import APIRouter
from app.utils.http_client import get_http_client
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Проверка здоровья Gateway и всех backend сервисов
    """
    services_status = {}
    client = get_http_client()

    # Проверяем Auth Service
    try:
        response = await client.get(f"{settings.AUTH_SERVICE_URL}/health", timeout=5.0)
        services_status["auth_service"] = {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "response_time_ms": response.elapsed.total_seconds() * 1000,
        }
    except httpx.TimeoutException:
        services_status["auth_service"] = {
            "status": "timeout",
            "error": "Service took too long to respond",
        }
    except httpx.ConnectError as e:
        services_status["auth_service"] = {"status": "unreachable", "error": str(e)}
    except Exception as e:
        services_status["auth_service"] = {"status": "error", "error": str(e)}

    # Проверяем Main Service
    try:
        response = await client.get(f"{settings.MAIN_SERVICE_URL}/health", timeout=5.0)
        services_status["main_service"] = {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "response_time_ms": response.elapsed.total_seconds() * 1000,
        }
    except httpx.TimeoutException:
        services_status["main_service"] = {
            "status": "timeout",
            "error": "Service took too long to respond",
        }
    except httpx.ConnectError as e:
        services_status["main_service"] = {"status": "unreachable", "error": str(e)}
    except Exception as e:
        services_status["main_service"] = {"status": "error", "error": str(e)}

    # Gateway считается здоровым, если хотя бы один сервис доступен
    all_healthy = any(s.get("status") == "healthy" for s in services_status.values())

    return {
        "gateway": "healthy",
        "services": services_status,
        "overall": "healthy" if all_healthy else "degraded",
    }
