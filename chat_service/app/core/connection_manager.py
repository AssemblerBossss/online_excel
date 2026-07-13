import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Активные WebSocket-соединения ТОЛЬКО этой реплики chat_service,
    сгруппированные по email. Глобальную видимость между репликами
    даёт Redis Pub/Sub (см. realtime.py).
    """

    def __init__(self):
        # Хранилище активных WebSocket соединений
        # Ключ: email пользователя
        # Значение: множество WebSocket соединений (у пользователя может быть несколько вкладок/устройств)
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, email: str, websocket: WebSocket) -> None:
        """Принять новое WebSocket соединение и сохранить его.

        Args:
            email: Email пользователя
            websocket: Объект WebSocket соединения
        """
        await websocket.accept()  # Подтверждаем WebSocket handshake
        self._connections[email].add(websocket)  # Добавляем соединение в хранилище
        logger.info(
            f"WS подключен : {email}, всего соединений: {len(self._connections[email])}"
        )

    def disconnect(self, email: str, websocket: WebSocket) -> None:
        """Закрыть и удалить WebSocket соединение.

        Args:
            email: Email пользователя
            websocket: Объект WebSocket соединения
        """
        self._connections[email].discard(
            websocket
        )  # Удаляем соединение (discard безопасен, если его нет)
        if not self._connections[email]:  # Если у пользователя больше нет соединений
            del self._connections[email]  # Удаляем запись о пользователе
        logger.info(f"WS отключен: {email}")

    async def send_to_local(self, email: str, payload: dict) -> None:
        """Отправить сообщение всем WebSocket соединениям пользователя в этой реплике.

        Args:
            email: Email получателя
            payload: Данные для отправки (будут сериализованы в JSON)

        Note:
            - Отправляет только локальным соединениям (в этой реплике)
            - Удаляет "мёртвые" соединения (которые закрылись или упали с ошибкой)
        """
        dead = []  # Список соединений, которые нужно удалить
        for ws in self._connections.get(
            email, set()
        ):  # Проходим по всем соединениям пользователя
            try:
                await ws.send_json(payload)  # Отправляем сообщение
            except Exception:  # Если соединение закрыто или ошибка
                dead.append(ws)  # Помечаем для удаления
        for ws in dead:  # Удаляем мёртвые соединения
            self.disconnect(email, ws)


# Глобальный экземпляр менеджера соединений (синглтон)
connection_manager = ConnectionManager()
