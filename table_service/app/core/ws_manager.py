import asyncio
import logging

from fastapi import WebSocket
from redis.asyncio import Redis
from urllib3.contrib.emscripten import connection

logger = logging.getLogger(__name__)

EVENTS_PATTERN = "events:rows:*"


class TableWsManager:
    """Реестр WS-подключений по table_id + фанаут событий из Redis Pub/Sub."""

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}

    async def connect(self, table_id: int, websocket: WebSocket) -> None:
        """Подключить WebSocket клиента к указанной таблице и добавить соединение в пул активных подключений."""
        await websocket.accept()
        self._connections.setdefault(table_id, set()).add(websocket)

    async def disconnect(self, table_id: int, websocket: WebSocket) -> None:
        """Удалить WebSocket соединение из пула активных подключений к таблице."""
        connections: set[WebSocket] | None = self._connections.get(table_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(table_id, None)
