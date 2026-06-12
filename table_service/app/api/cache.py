# table_service/app/api/cache.py
from redis.asyncio import Redis

TABLES_CACHE_KEY = "tables:all"
TRASH_CACHE_KEY = "tables:trash"
TABLES_CACHE_TTL = 120


async def invalidate_tables_cache(redis: Redis) -> None:
    await redis.delete(TABLES_CACHE_KEY)
