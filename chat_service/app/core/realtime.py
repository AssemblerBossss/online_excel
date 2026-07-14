import logging

from chat_service.app.core.connection_manager import connection_manager
from chat_service.app.core.settings import app_settings
from chat_service.app.infrastructure import RedisPubSub

logger = logging.getLogger(__name__)

redis_pubsub = RedisPubSub(redis_url=app_settings.REDIS_URL)


async def dispatch_event(event: dict) -> None:
    """Вызывается при получении события из Redis"""
    target_email = event.get("target_email")
    if not target_email:
        logger.warning(f"Событие без target_email проигнорировано: {event}")
        return
    await connection_manager.send_to_local(target_email, event)


async def publish_new_message(target_email: str, chat_id, message) -> None:
    await redis_pubsub.publish(
        {
            "type": "new_message",
            "target_email": target_email,
            "chat_id": str(chat_id),
            "message": {
                "id": str(message.id),
                "sender_email": message.sender_email,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
                "is_read": message.is_read,
            },
        }
    )
