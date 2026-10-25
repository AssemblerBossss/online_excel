import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from table_service.app.api.dependencies import (
    get_async_uow_session,
    get_current_active_user,
    get_sheet_service,
)
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.schemas import (
    SCurrentUser,
    SSheetBatch,
    SSheetBatchResult,
    SSheetSnapshot,
)
from table_service.app.services import SheetService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/{table_id}//sheet", response_model=SSheetSnapshot, status_code=status.HTTP_200_OK
)
async def get_sheet(
    sheet_service: Annotated[SheetService, Depends(get_sheet_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
) -> SSheetSnapshot:
    return await sheet_service.get_snapshot(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )


@router.post(
    "/{table_id}//sheet/batch",
    response_model=SSheetBatchResult,
    status_code=status.HTTP_200_OK,
)
async def apply_sheet_batch(
    batch: SSheetBatch,
    sheet_service: Annotated[SheetService, Depends(get_sheet_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
) -> SSheetSnapshot:
    """Применить пакет изменений: структурная операция, ячейки, оформление, meta."""
    return await sheet_service.apply_batch(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
        batch=batch,
    )
