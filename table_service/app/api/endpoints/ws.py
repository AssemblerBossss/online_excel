import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from table_service.app.api.dependencies import (
    get_async_uow_session,
    get_data_service,
    get_ws_ticket_service,
)
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.core.ws_manager import table_ws_manager
from table_service.app.exceptions import AppException
from table_service.app.services import DataService
from table_service.app.services.ws_ticket import WsTicketService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/tables/{table_id}")
async def table_ws_events(
    websocket: WebSocket,
    ticket_service: Annotated[WsTicketService, Depends(get_ws_ticket_service)],
    data_service: Annotated[DataService, Depends(get_data_service)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(ge=1),
    ticket: str = Query(...),
):
    """Подписка на события строк таблицы. Аутентификация — одноразовым тикетом в query."""
    try:
        user = await ticket_service.redeem(ticket)
        await data_service.ensure_read_access(
            uow_session=uow_session,
            table_id=table_id,
            user_id=user.user_id,
            user_role=user.role,
        )
    except AppException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await table_ws_manager.connect(table_id=table_id, websocket=websocket)
    try:
        while True:
            await websocket.receive_text()  # клиент ничего не шлёт; ждём разрыва
    except WebSocketDisconnect:
        pass
    finally:
        table_ws_manager.disconnect(table_id, websocket)
