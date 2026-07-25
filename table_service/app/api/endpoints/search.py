from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette import status

from table_service.app.api.dependencies import get_current_user, get_search_service
from table_service.app.services import SearchService

router = APIRouter()


@router.get(
    "/", dependencies=[Depends(get_current_user)], status_code=status.HTTP_200_OK
)
async def search(
    q: Annotated[str, Query(min_length=1, max_length=200)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """Поиск таблиц по названию и описанию."""
    return await search_service.search_tables(query=q, limit=limit)
