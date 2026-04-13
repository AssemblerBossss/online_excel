import uuid
import aio_pika
import asyncio
from typing import Optional
from aio_pika.abc import AbstractIncomingMessage
from typing_extensions import deprecated

from table_service.app.core.settings import app_settings

RABBITMQ_URL = app_settings.RABBITMQ_URL


@deprecated("RPC-валидация пользователей не подключена")
class RpcClient:
    """Асинхронный RPC клиент для RabbitMQ."""

    def __init__(self, amqp_url: str = RABBITMQ_URL) -> None:
        """Инициализирует RPC клиент с URL для подключения к RabbitMQ."""
        self.amqp_url = amqp_url
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.callback_queue: Optional[aio_pika.RobustQueue] = None
        self.futures = {}
        self.loop = asyncio.get_running_loop()

    async def connect(self) -> None:
        """Устанавливает соединение с RabbitMQ, создает канал и очередь для ответов."""
        self.connection = await aio_pika.connect_robust(self.amqp_url, loop=self.loop)
        self.channel = await self.connection.channel()
        self.callback_queue = await self.channel.declare_queue(exclusive=True)
        await self.callback_queue.consume(self.on_response, no_ack=True)

    async def close(self) -> None:
        """Закрывает соединение с RabbitMQ, если оно открыто."""
        if self.connection and not self.connection.closed:
            await self.connection.close()

    async def on_response(self, message: AbstractIncomingMessage) -> None:
        """Обрабатывает входящие ответы, резолвит соответствующий future по correlation_id."""
        future: Optional[asyncio.Future] = self.futures.pop(
            message.correlation_id, None
        )
        if future:
            future.set_result(message.body)

    async def call(self, user_id: int) -> Optional[bytes]:
        """
        Отправляет запрос в очередь и ожидает ответ.

        Args:
            user_id: ID пользователя для проверки

        Returns:
            Ответ от сервера или None при таймауте

        Raises:
            ConnectionError: Если клиент не подключен к RabbitMQ
        """
        if not self.connection or self.connection.is_closed:
            raise ConnectionError("RPC Client is not connected.")

        correlation_id = str(uuid.uuid4())
        future = self.loop.create_future()
        self.futures[correlation_id] = future

        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=str(user_id).encode(),
                correlation_id=correlation_id,
                reply_to=self.callback_queue.name,
            ),
            routing_key="user_check_queue",
        )

        try:
            return await asyncio.wait_for(future, timeout=5.0)
        except asyncio.TimeoutError:
            self.futures.pop(correlation_id, None)
            return None
