from __future__ import annotations
import json
import logging
import os
from datetime import datetime

import aio_pika

from table_service.app.core.database import AsyncSessionFactory
from table_service.app.infrastructure import EventConsumerBase

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL")


class UserEventConsumer:
    def __init__(self):
        self._base = EventConsumerBase()

    async def connect(self) -> None:
        await self._base.connect(
            exchange_name="user.events",
            queue_name="table_service.user_events",
            routing_keys=["user.registered", "user.updated", "user.deleted"],
            callback=self._handle_message,
        )
        logger.info("UserEventConsumer подключён и слушает события")

    async def close(self) -> None:
        await self._base.close()
        logger.info("UserEventConsumer отключён")

    async def _handle_message(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process():
            try:
                event_type = message.type
                body = json.loads(message.body.decode())

                logger.info(
                    f"Получено событие: {event_type}, user_id={body.get('user_id')}"
                )

                async with AsyncSessionFactory() as session:
                    from table_service.app.repository import UserRepository

                    repo = UserRepository(session=session)
                    await self._dispatch(event_type, body, repo)

            except Exception as e:
                logger.error(f"Ошибка обработки события: {e}", exc_info=True)

    async def _dispatch(
        self, event_type: str, body: dict, repo: "UserRepository"
    ) -> None:
        if event_type in ("user.registered", "user.updated"):

            timestamp = datetime.fromisoformat(body["timestamp"].replace("Z", "+00:00"))
            # Берём только значение роли без префикса класса
            role = body["role"].split(".")[-1].lower()
            await repo.upsert(
                {
                    "id": int(body["user_id"]),
                    "email": body["email"],
                    "role": role,
                    "timestamp": timestamp,
                }
            )

            logger.info(f"UserProjection upsert для user_id={body['user_id']}")

        elif event_type == "user.deleted":
            await repo.mark_deleted(int(body["user_id"]))
            logger.info(f"UserProjection mark_deleted для user_id={body['user_id']}")

        else:
            logger.warning(f"Неизвестный тип события: {event_type}")


user_event_consumer = UserEventConsumer()
