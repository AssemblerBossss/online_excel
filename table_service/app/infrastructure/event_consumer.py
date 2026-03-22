import os
import aio_pika
from aio_pika import ExchangeType
from typing import Callable

RABBITMQ_URL = os.getenv("RABBITMQ_URL")


class EventConsumerBase:
    """
    Базовый класс для консьюмеров событий RabbitMQ.
    Инкапсулирует низкоуровневую логику подключения,
    объявления exchange/queue и биндинга routing keys.
    """

    def __init__(self, amqp_url: str = RABBITMQ_URL):
        self.amqp_url = amqp_url
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.RobustChannel | None = None

    async def connect(
        self,
        exchange_name: str,
        queue_name: str,
        routing_keys: list[str],
        callback: Callable,
    ) -> None:
        """
        Устанавливает соединение, объявляет exchange и очередь,
        биндит routing keys и запускает консьюмер.

        Args:
            exchange_name: Имя exchange (topic)
            queue_name: Имя очереди
            routing_keys: Список routing keys для биндинга
            callback: Функция обработки входящих сообщений
        """
        self.connection = await aio_pika.connect_robust(url=self.amqp_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)

        exchange = await self.channel.declare_exchange(
            exchange_name, ExchangeType.TOPIC, durable=True
        )

        queue = await self.channel.declare_queue(name=queue_name, durable=True)
        for routing_key in routing_keys:
            await queue.bind(exchange, routing_key=routing_key)

        await queue.consume(callback)

    async def close(self) -> None:
        """Закрывает соединение с RabbitMQ если оно открыто."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
