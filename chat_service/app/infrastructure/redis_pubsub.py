import json
import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisPubSub:
    """Класс для работы с Redis Pub/Sub и временными токенами (тикетами).

    Используется для:
    1. Обмена сообщениями между сервисами через Pub/Sub
    2. Хранения одноразовых токенов для WebSocket подключений
    """

    CHANNEL = "chat:events"  # Канал для обмена событиями чата
    TICKET_PREFIX = "ws_ticket:"  # Префикс для ключей тикетов в Redis

    def __init__(self, redis_url: str):
        """Инициализация RedisPubSub.

        Args:
            redis_url: URL для подключения к Redis (например, redis://localhost:6379)
        """
        self._redis_url = redis_url
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None

    async def connect(self) -> None:
        """Подключение к Redis и подписка на канал.

        Создаёт:
        - Клиент Redis для публикации сообщений
        - PubSub объект для подписки на канал

        После вызова этого метода класс готов к работе.
        """
        self._redis = redis.from_url(self._redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(self.CHANNEL)
        logger.info(f"Redis PubSub подключён, канал: {self.CHANNEL}")

    async def publish(self, payload: dict) -> None:
        """Публикация события в канал Redis.

        Отправляет JSON-сообщение всем подписчикам канала CHANNEL.

        Args:
            payload: Словарь с данными события (будет сериализован в JSON)

        Raises:
            RuntimeError: Если Redis не подключён
        """
        if not self._redis:
            raise RuntimeError("RedisPubSub не подключён")
        await self._redis.publish(self.CHANNEL, json.dumps(payload))

    async def listen(self, handler: Callable[[dict], Awaitable[None]]) -> None:
        """Прослушивание канала и обработка входящих сообщений.

        Бесконечно слушает канал и вызывает handler для каждого сообщения.
        Работает в асинхронном режиме (обычно запускается как background-задача).

        Args:
            handler: Асинхронная функция, которая принимает словарь с данными события

        Raises:
            RuntimeError: Если Redis не подключён
        """
        if not self._pubsub:
            raise RuntimeError("RedisPubSub не подключён")
        async for message in self._pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                await handler(data)  # Вызов обработчика
            except Exception:
                logger.exception("Ошибка обработки события из RedisPubSub")

    async def store_ticket(self, ticket: str, user_email: str, ttl: int) -> None:
        """Сохранение одноразового тикета для WebSocket подключения.

        Тикет — это временный токен, который позволяет пользователю
        подключиться к WebSocket без повторной аутентификации.

        Args:
            ticket: Уникальная строка-токен
            user_email: Email пользователя, которому выдан тикет
            ttl: Время жизни тикета в секундах (Time To Live)

        Raises:
            RuntimeError: Если Redis не подключён
        """
        if not self._redis:
            raise RuntimeError("RedisPubSub не подключен")
        await self._redis.set(f"{self.TICKET_PREFIX}{ticket}", user_email, ex=ttl)

    async def consume_ticket(self, ticket: str) -> str | None:
        """Получение и удаление тикета (одноразовое использование).

        Используется при WebSocket подключении: клиент передаёт тикет,
        сервер проверяет его и сразу удаляет (GETDEL).

        Args:
            ticket: Уникальная строка-токен

        Returns:
            Email пользователя, если тикет валидный, иначе None

        Raises:
            RuntimeError: Если Redis не подключён
        """
        if not self._redis:
            raise RuntimeError("RedisPubSub не подключён")
        return await self._redis.getdel(f"{self.TICKET_PREFIX}{ticket}")

    async def close(self) -> None:
        """Закрытие соединения с Redis.

        Отписывается от канала, закрывает PubSub и клиент Redis.
        Вызывается при завершении работы приложения.
        """
        if self._pubsub:
            await self._pubsub.unsubscribe(self.CHANNEL)
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
