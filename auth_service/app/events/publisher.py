import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractChannel, AbstractExchange

from auth_service.app.config import auth_service_settings as settings
from auth_service.app.schemas import BaseEvent


class EventPublisher:
    def __init__(self):
        self.connection: AbstractRobustConnection | None = None
        self.channel: AbstractChannel | None = None
        self.exchange: AbstractExchange | None = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            "user.events", aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def publish(self, event: BaseEvent):
        message = aio_pika.Message(
            body=event.model_dump_json().encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
            type=event.event_type,
        )
        await self.exchange.publish(message=message, routing_key=event.event_type)

    async def disconnect(self):
        if self.connection:
            await self.connection.close()


event_publisher = EventPublisher()
