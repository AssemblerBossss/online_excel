"""
Клиент Elasticsearch для chat_service.

Индекс `chat_users` хранит денормализованную проекцию пользователей
для быстрого prefix-поиска по email (и в будущем — по имени/фамилии мб).

PostgreSQL остаётся единственным источником истины; ES — read-only модель,
синхронизируемая через RabbitMQ-события в UserEventConsumer.
"""

import logging

from elasticsearch import AsyncElasticsearch, NotFoundError, ConnectionError as ESConnectionError
from chat_service.app.core.settings import app_settings


logger = logging.getLogger(__name__)

USERS_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                # Для future use: поиск по имени с lowercasing
                "lowercase_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"],
                }
            }
        },
    },
    "mappings": {
        "properties": {
            "user_id": {"type": "integer"},
            "email": {"type": "keyword", "normalizer": None},
            "first_name": {
                "type": "text",
                "analyzer": "lowercase_analyzer",
                "fields": {"raw": {"type": "keyword"}},
            },
            "last_name": {
                "type": "text",
                "analyzer": "lowercase_analyzer",
                "fields": {"raw": {"type": "keyword"}},
            },
            "is_active": {"type": "boolean"},
        }
    },
}


class ElasticsearchClient:
    """
    Обёртка над AsyncElasticsearch с ленивой инициализацией
    и graceful handling ошибок подключения.
    """

    def __init__(self) -> None:
        self._client: AsyncElasticsearch | None = None
        self._index_name: str = app_settings.ES_INDEX_NAME

    @property
    def client(self) -> AsyncElasticsearch:
        # Ленивая инициализация: клиент создаётся при первом обращении
        if self._client is None:
            self._client = AsyncElasticsearch(
                hosts=[app_settings.ES_HOST],
                request_timeout=5.0,
                retry_on_timeout=True,
                max_retries=5
            )
        return self._client

    @property
    def index_name(self) -> str:
        return self._index_name

    async def is_available(self) -> bool:
        """Проверяет доступность ES без выбрасывания исключений."""
        try:
            exists = await self.client.ping()
        except ESConnectionError:
            return False
        except Exception as exc:
            logger.warning("Неожиданная ошибка при проверке ES: %s", exc)
            return False

    async def ensure_index(self) -> None:
        """Создает индекс с нужным маппингом, если его нет"""
        try:
            exists = await self.client.indices.exists(self.index_name)
            if not exists:
                await self.client.indices.create(
                    index=self._index_name,
                    body=USERS_INDEX_MAPPING
                )
                logger.info("Создан ES-индекс '%s'", self._index_name)
            else:
                logger.info("ES-индекс '%s' уже существует", self._index_name)
        except ESConnectionError:
            logger.error(
                "Не удалось подключиться к Elasticsearch (%s). "
                "Поиск пользователей будет работать в fallback-режиме через PostgreSQL.",
                app_settings.ES_URL,
            )
        except Exception as exc:
            logger.exception("Ошибка при инициализации ES-индекса: %s", exc)

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()
            self._client = None

es_client = ElasticsearchClient()





