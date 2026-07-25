from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import aio_pika

from chat_service.app.core.database import AsyncSessionFactory
from chat_service.app.core.settings import app_settings
from chat_service.app.infrastructure import EventConsumerBase

if TYPE_CHECKING:
    from chat_service.app.repository import UserRepository

logger = logging.getLogger(__name__)


class UserEventConsumer:
    EXCHANGE_NAME = "user.events"
    QUEUE_NAME = "chat_service.user_events"
    ROUTING_KEYS = ["user.registered", "user.updated", "user.deleted"]

    def __init__(self) -> None:
        self._base = EventConsumerBase(amqp_url=app_settings.RABBITMQ_URL)


    async def connect(self) -> None:
        await self._base.connect(
            exchange_name=self.EXCHANGE_NAME,
            queue_name=self.QUEUE_NAME,
            routing_key=self.ROUTING_KEYS,
            callback=self._handle_message,
        )
        logger.info("UserEventConsumer подключён и слушает события auth_service")

    async def close(self) -> None:
        await self._base.close()
        logger.info("UserEventConsumer отключен")

    async def _dispatch(
        self, event_type: str, body: dict, repo: "UserRepository"
    ) -> None:
        user_id = int(body["user_id"])

        if event_type in ("user.registered", "user.updated"):
            # Поддержка ISO формата с 'Z' для Python 3.11+ и старых версий
            timestamp_str = body["timestamp"]
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"
            timestamp = datetime.fromisoformat(timestamp_str)

            role = body.get("role", "").split(".")[-1].lower()

            await repo.upsert(
                {
                    "id": user_id,
                    "email": body["email"],
                    "role": role,
                    "timestamp": timestamp,
                }
            )
            logger.info(f"Локальная копия пользователя upsert: user_id={user_id}")

        elif event_type == "user.deleted":
            await repo.mark_deleted(user_id)
            logger.info(
                f"Локальная копия пользователя помечена как удалённая: user_id={user_id}"
            )

        else:
            logger.warning(f"Неизвестный тип события для chat_service: {event_type}")

    async def _handle_message(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process():
            try:
                event_type = message.type
                body = json.loads(message.body.decode())

                logger.info(
                    f"Получено событие: {event_type}, user_id={body.get('user_id')}"
                )

                async with AsyncSessionFactory() as session:
                    # Импорт внутри функции для избежания циклических зависимостей
                    from chat_service.app.repository import UserRepository

                    repo = UserRepository(session=session)
                    await self._dispatch(event_type, body, repo)

            except Exception as e:
                logger.error(
                    f"Ошибка обработки события {message.type}: {e}", exc_info=True
                )
                # Сообщение будет nack'нуто и requeue'нуто благодаря message.process()


# Синглтон-экземпляр для использования в lifecycle приложения
user_event_consumer = UserEventConsumer()
