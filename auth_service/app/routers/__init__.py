from .auth import router as auth_router
from .user import router as user_router
from .health import router as health_router

__all__ = ["auth_router", "user_router", "health_router"]
