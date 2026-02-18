from table_service.app.infrastructure import RpcClient


class RabbitMQCategoryValidator:
    """Конкретная реализация валидатора категорий через RabbitMQ RPC."""

    def __init__(self):
        self.rpc_client = RpcClient()

    async def connect(self):
        await self.rpc_client.connect()

    async def close(self):
        await self.rpc_client.close()

    async def check_exists(self, user_id: int) -> bool:
        response = await self.rpc_client.call(user_id)
        if response is None:
            return False
        return response == b"true"
