from .ws import router as ws_router
from .sheet import router as sheet_router
from .trash import router as trash_router
from .health import router as health_router
from .search import router as search_router
from .tables import router as tables_router
from .permissions import router as permissions_router


__all__ = [
    "sheet_router",
    "health_router",
    "permissions_router",
    "search_router",
    "tables_router",
    "trash_router",
    "ws_router",
]
