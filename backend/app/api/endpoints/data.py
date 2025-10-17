from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query
)


router = APIRouter(prefix="/data", tags=["data"])

@router.get("{table_id}/rows", response_model=List[TableRowResponce])
async def list_table_rows(
        table_id: int,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = Query(None),
        data_service: Annotated[TaskService, Depends(get_task_service)],

):
    rows: TableRowResponce = await data_service.get_table_rows(table_id, user.id, skip=skip, limit=limit)
    return rows
