import logging
from typing import Any

from elasticsearch import NotFoundError

from chat_service.app.core.es_client import ElasticsearchClient

logger = logging.getLogger(__name__)


class ElasticSearchUserRepository:
    """
    Репозиторий для работы с индексом пользователей в ElasticSearch
    """

    def __init__(self, client: ElasticsearchClient):
        self._client = client
        self._index = client.index_name

    async def upsert(
        self,
        user_id: int,
        email: str,
        first_name: str,
        last_name: str,
        is_active: bool,
    ) -> None:
        """Создает или обновляет документ пользователя"""
        document: dict[str, Any] = {
            "user_id": user_id,
            "email": email,
            "first_name": first_name or "",
            "last_name": last_name or "",
            "is_active": is_active,
        }

        await self._client.client.index(
            index=self._index, id=str(user_id), document=document
        )
        logger.debug("ES upsert: user_id=%s", user_id)

    async def deactivate_user(self, user_id: int) -> None:
        """Помечает пользователя как неактивного"""
        try:
            await self._client.client.update(
                index=self._index, id=str(user_id), doc={"is_active": False}
            )
            logger.debug("ES deactivate_user: user_id=%s", user_id)
        except NotFoundError:
            logger.warning(
                "ES cannot find a user for deactivation: user_id=%s", user_id
            )

    async def search_by_email_prefix(
        self, prefix: str, exclude_email: str, limit: int = 5
    ) -> list[str]:
        """
        Ищет email по префиксу
        Возвращает список адресов, отсортированных по алфавиту
        """

        query = {
            "bool": {
                "must": [
                    {"prefix": {"email": prefix}},
                    {"term": {"is_active": True}},
                ],
                "must_not": [
                    {"term": {"email": exclude_email.lower()}},
                ],
            }
        }

        response = await self._client.client.search(
            index=self._index,
            query=query,
            size=limit,
            sort=[{"email": {"order": "asc"}}],
            _source=["email"],
        )
        return [hit["_source"]["email"] for hit in response["hits"]["hits"]]
