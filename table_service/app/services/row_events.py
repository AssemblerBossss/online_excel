import logging

from redis.asyncio import Redis

from table_service.app.schemas import SRowEvent

logger = logging.getLogger(__name__)


def rows_channel(table_id: int) -> str:
    return f"events:rows:{table_id}"


class RowEventPublisher:
    """Публикует события строк в Redis Pub/Sub для WS-подписчиков."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish(self, event: SRowEvent) -> None:
        try:
            await self.redis.publish(
                rows_channel(event.table_id), event.model_dump_json()
            )
        except Exception:
            logger.exception("Не удалось опубликовать событие %s", event.event)
