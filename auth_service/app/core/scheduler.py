import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from auth_service.app.repository.token import TokenRepository

# Берем фабрику сессий напрямую из ядра. main.py об этом даже не догадывается.
from .database import async_session_maker

logger = logging.getLogger(__name__)


class TokenCleanupScheduler:
    """Планировщик для периодической очистки истёкших токенов."""

    def __init__(self):
        self._scheduler = AsyncIOScheduler()

    async def _cleanup_expired_tokens(self) -> None:
        """Выполняет очистку истёкших токенов."""
        try:
            # Создаем независимую сессию специально для фоновой задачи
            async with async_session_maker() as session:
                repo = TokenRepository(session)
                deleted = await repo.delete_expired()
                await session.commit()

                if deleted > 0:
                    logger.info("🧹 Удалено %d истекших refresh-токенов", deleted)
        except Exception as e:
            logger.exception("Ошибка при очистке истекших токенов: %s", e)

    def start(self) -> None:
        """Запускает планировщик."""
        self._scheduler.add_job(
            self._cleanup_expired_tokens,
            trigger="interval",
            hours=6,
            id="cleanup_expired_tokens",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("✅ Планировщик очистки токенов запущен (интервал: 6 часов)")

    def stop(self) -> None:
        """Останавливает планировщик."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("🛑 Планировщик очистки токенов остановлен")


# Создаем единственный экземпляр планировщика
_scheduler = TokenCleanupScheduler()


@asynccontextmanager
async def scheduler_lifespan():
    """Контекстный менеджер для управления жизненным циклом планировщика."""
    _scheduler.start()
    try:
        yield
    finally:
        _scheduler.stop()
