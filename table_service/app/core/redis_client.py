from redis.asyncio import Redis

from table_service.app.core.settings import app_settings

_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            host=app_settings.CACHE_HOST,
            port=app_settings.CACHE_PORT,
            db=app_settings.CACHE_DB,
            encoding="utf8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
