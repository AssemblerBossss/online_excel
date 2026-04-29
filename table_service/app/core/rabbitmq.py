from typing_extensions import deprecated

from table_service.app.infrastructure import RpcClient


@deprecated("RPC-валидация пользователей не подключена")
class RabbitMQUserValidator:
    """Конкретная реализация валидатора категорий через RabbitMQ RPC."""

    def __init__(self):
        """Инициализирует новый экземпляр RabbitMQCategoryValidator"""
        self.rpc_client = RpcClient()

    async def connect(self):
        """Устанавливает соединение RPC через внутренний RpcClient"""
        await self.rpc_client.connect()

    async def close(self):
        """Закрывает соединение RPC через внутренний RpcClient"""
        await self.rpc_client.close()

    async def check_exists(self, user_id: int) -> bool:
        """Проверяет существование пользователя по его ID"""
        response = await self.rpc_client.call(user_id)
        if response is None:
            return False
        return response == b"true"


_user_validator_instance = None


def get_user_validator():
    """Lazy initialization — создаёт инстанс только при первом вызове."""
    global _user_validator_instance
    if _user_validator_instance is None:
        _user_validator_instance = RabbitMQUserValidator()
    return _user_validator_instance
