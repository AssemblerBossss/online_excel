import aio_pika
from aio_pika import ExchangeType
from typing import Callable

from chat_service.app.core.settings import app_settings


class EventConsumerBase:
    """
    Базовый класс для консьюмеров событий RabbitMQ.
    Инкапсулирует низкоуровневую логику подключения,
    объявления exchange/queue и биндинга routing keys.
    """

    def __init__(self, amqp_url: str | None = None):
        self.amqp_url = amqp_url or app_settings.RABBITMQ_URL
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.RobustChannel | None = None

    async def connect(
        self,
        exchange_name: str,
        queue_name: str,
        routing_key: list[str],
        callback: Callable,
    ) -> None:
        self.connection = await aio_pika.connect_robust(url=self.amqp_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)

        exchange = await self.channel.declare_exchange(
            exchange_name, ExchangeType.TOPIC, durable=True
        )

        queue = await self.channel.declare_queue(queue_name, durable=True)
        for routing_key in routing_key:
            await queue.bind(exchange, routing_key=routing_key)
        await queue.consume(callback)

    async def close(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
