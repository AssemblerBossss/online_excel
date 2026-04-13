import logging
from elasticsearch import AsyncElasticsearch


class SearchService:
    def __init__(self, es_client: AsyncElasticsearch):
        self.es_client = es_client

    async def search_tables(self, query: str, limit: int = 20) -> list[dict]:
        pass

    async def index_table(self):
        pass
