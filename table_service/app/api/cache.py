# table_service/app/api/cache.py
from redis.asyncio import Redis

TABLES_CACHE_PREFIX = "tables:list:"
TRASH_CACHE_PREFIX = "tables:trash:"
TABLES_CACHE_TTL = 120


def tables_cache_key(user_id: int) -> str:
    return f"{TABLES_CACHE_PREFIX}{user_id}"


def trash_cache_key(user_id: int) -> str:
    return f"{TRASH_CACHE_PREFIX}{user_id}"


async def invalidate_tables_cache(redis: Redis) -> None:
    async for key in redis.scan_iter(match=f"{TABLES_CACHE_PREFIX}*"):
        await redis.delete(key)


async def invalidate_trash_cache(redis: Redis) -> None:
    async for key in redis.scan_iter(match=f"{TRASH_CACHE_PREFIX}*"):
        await redis.delete(key)
