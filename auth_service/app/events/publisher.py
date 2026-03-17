import os
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from pydantic import BaseModel


RABBITMQ_URL = os.getenv("RABBITMQ_URL")


class EventPublisher:
    def __init__(self):
        self.connection: aio_pika.Connection = None
        self.channel: aio_pika.Channel = None
        self.exchange: aio_pika.Exchange = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            "user.events", ExchangeType.TOPIC, durable=True
        )

    async def publish(self, event: BaseModel):
        message = Message(
            body=event.model_dump_json().encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
            type=event.event_type,
        )
        await self.exchange.publish(message=message, routing_key=event.event_type)

    async def disconnect(self):
        if self.connection:
            await self.connection.close()


event_publisher = EventPublisher()
