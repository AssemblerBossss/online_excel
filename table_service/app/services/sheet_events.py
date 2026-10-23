import logging

from redis.asyncio import Redis

from table_service.app.schemas import SSheetEvent

logger = logging.getLogger(__name__)


def sheet_channel(table_id: int) -> str:
    return f"events:sheet:{table_id}"


class SheetEventPublisher:
    """Публикует события листа в Redis Pub/Sub для WS-подписчиков."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish(self, event: SSheetEvent) -> None:
        try:
            await self.redis.publish(
                sheet_channel(event.table_id), event.model_dump_json()
            )
        except Exception:
            logger.exception("Не удалось опубликовать событие %s", event.table_id)
