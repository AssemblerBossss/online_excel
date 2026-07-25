from .auth import router as auth_router
from .health import router as health_router
from .user import router as user_router

__all__ = ["auth_router", "health_router", "user_router"]
