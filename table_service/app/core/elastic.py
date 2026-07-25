from elasticsearch import AsyncElasticsearch

from table_service.app.core.settings import app_settings

_es_client: AsyncElasticsearch | None = None

TABLE_INDEX = "tables"

INDEX_MAPPING = {
    "settings": {
        "number_of_replicas": 0,
        "analysis": {
            "tokenizer": {
                "ngram_tokenizer": {
                    "type": "ngram",
                    "min_gram": 3,
                    "max_gram": 4,
                    "token_chars": ["letter", "digit"],
                }
            },
            "analyzer": {
                "text_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "stop"],
                },
                "search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
                "ngram_analyzer": {
                    "type": "custom",
                    "tokenizer": "ngram_tokenizer",
                    "filter": ["lowercase", "asciifolding"],
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "name": {
                "type": "text",
                "analyzer": "text_analyzer",
                "search_analyzer": "search_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "ngram": {
                        "type": "text",
                        "analyzer": "ngram_analyzer",
                    },
                },
            },
            "description": {
                "type": "text",
                "analyzer": "text_analyzer",
                "search_analyzer": "search_analyzer",
            },
            "is_public": {"type": "boolean"},
            "created_by_id": {"type": "integer"},
        }
    },
}


async def get_es_client() -> AsyncElasticsearch:
    global _es_client
    if _es_client is None:
        _es_client = AsyncElasticsearch(
            hosts=[
                {
                    "host": app_settings.ES_HOST,
                    "port": app_settings.ES_PORT,
                    "scheme": "http",
                }
            ]
        )
    return _es_client


async def close_es_client() -> None:
    global _es_client
    if _es_client is not None:
        await _es_client.close()
        _es_client = None


async def init_es_index() -> None:
    """Создать индекс при старте приложения, если его нет."""
    es = await get_es_client()
    exists = await es.indices.exists(index=TABLE_INDEX)
    if not exists:
        await es.indices.create(index=TABLE_INDEX, body=INDEX_MAPPING)
