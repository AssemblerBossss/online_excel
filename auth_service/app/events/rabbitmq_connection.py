import aio_pika
from aio_pika import Connection, Exchange, Channel
from typing import Optional


class RabbitMQConnection:
    def __init__(self):
        self.connection: Optional[Connection] = None
        self.exchange: Optional[Exchange] = None
        self.channel: Optional[Channel] = None
