from enum import StrEnum

from redis.asyncio import Redis


class AccessLevel(StrEnum):
    READ = "read"
    WRITE = "write"
    MANAGE = "manage"


class AccessCache:
    """Кэш результатов проверки доступа с версионированием по таблице.

    Ключ доступа содержит версию таблицы:
        perm:{level}:table:{table_id}:v{version}:user:{user_id}

    Любое изменение, влияющее на доступ (выдача/изменение/отзыв прав,
    смена is_public, удаление/восстановление таблицы), делает bump_table():
    версия растёт, и все старые ключи перестают читаться. Их не нужно
    искать и удалять, они сами протухают по TTL.
    """

    # Версия должна жить заметно дольше, чем TTL ключей доступа,
    # иначе после сброса версии в 0 могут "ожить" старые ключи.
    VERSION_TTL = 24 * 60 * 60

    def __init__(self, redis: Redis, ttl: int = 60):
        self.redis = redis
        self.ttl = ttl

    @staticmethod
    def _version_key(table_id: int) -> str:
        return f"perm:ver:table:{table_id}"

    @staticmethod
    def _key(table_id: int, user_id: int, level: AccessLevel, version: int) -> str:
        return f"perm:{level.value}:table:{table_id}:v{version}:user:{user_id}"

    async def _get_version(self, table_id: int) -> int:
        raw = await self.redis.get(self._version_key(table_id))
        return int(raw) if raw is not None else 0

    async def lookup(
        self, table_id: int, user_id: int, level: AccessLevel
    ) -> tuple[int, bool | None]:
        """Возвращает (версия, результат). Результат None, если в кэше пусто.

        Версию нужно передать обратно в store(): так мы записываем результат
        под той версией, которую видели ДО похода в БД. Если права изменились
        во время проверки, запись уйдёт в уже устаревший ключ и никому не повредит.
        """
        version = await self._get_version(table_id)
        raw = await self.redis.get(self._key(table_id, user_id, level, version))
        return version, (None if raw is None else raw == "1")

    async def store(
        self,
        table_id: int,
        user_id: int,
        level: AccessLevel,
        version: int,
        value: bool,
    ) -> None:
        await self.redis.setex(
            self._key(table_id, user_id, level, version),
            self.ttl,
            "1" if value else "0",
        )

    async def bump_table(self, table_id: int) -> None:
        """Сбросить кэш доступа всех пользователей для таблицы."""
        key = self._version_key(table_id)
        pipe = self.redis.pipeline(transaction=True)
        await pipe.incr(key)
        await pipe.expire(key, self.VERSION_TTL)
        await pipe.execute()
