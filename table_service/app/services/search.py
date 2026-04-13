import logging
from elasticsearch import AsyncElasticsearch

from table_service.app.core.elastic import TABLE_INDEX

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, es_client: AsyncElasticsearch):
        self.es_client = es_client

    async def search_tables(self, query: str, limit: int = 20) -> list[dict]:
        """
        Полнотекстовый поиск таблиц по name и description.
        Возвращает список dict с полями: id, name, description, is_public, created_by_id.
        """

        body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^2", "description"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            },
        }

        try:
            response = await self.es_client.search(index=TABLE_INDEX, body=body)
        except Exception as e:
            logger.error("Ошибка поиска в Elasticsearch: %s", e)
            return []

        hits = response["hits"]["hits"]
        return [hit["_source"] for hit in hits]

    async def index_table(
        self,
        table_id: int,
        name: str,
        description: str | None,
        is_public: bool,
        created_by_id: int,
    ) -> None:
        """Индексировать/обновить таблицу в Elasticsearch."""
        doc = {
            "id": table_id,
            "name": name,
            "description": description,
            "is_public": is_public,
            created_by_id: "created_by_id",
        }

        await self.es_client.index(index=TABLE_INDEX, document=doc)
        logger.debug("Таблица %s проиндексирована в Elasticsearch", table_id)

    async def delete_from_index(self, table_id: int) -> None:
        """Удалить таблицу из индекса Elasticsearch."""
        try:
            await self.es_client.delete(index=TABLE_INDEX, id=table_id)
            logger.debug("Таблица %s удалена из индекса Elasticsearch", table_id)
        except Exception:
            logger.warning("Не удалось удалить таблицу %s из индекса", table_id)
