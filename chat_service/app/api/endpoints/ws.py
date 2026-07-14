import logging
import secrets

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from chat_service.app.api.dependencies import get_current_user_email
from chat_service.app.core.connection_manager import connection_manager
from chat_service.app.core.realtime import redis_pubsub

logger = logging.getLogger(__name__)

router = APIRouter()

TICKET_TTL_SECONDS = 300


@router.post("/ws-ticket", summary="Получить одноразовый тикет для WS подключения")
async def issue_ws_ticket(user_email: str = Depends(get_current_user_email)) -> dict:
    ticket = secrets.token_urlsafe(32)
    await redis_pubsub.store_ticket(ticket, user_email, ttl=TICKET_TTL_SECONDS)
    return {"ticket": ticket, "expires_in": TICKET_TTL_SECONDS}


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket, ticket: str):
    user_email = await redis_pubsub.consume_ticket(ticket)
    if not user_email:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await connection_manager.connect(user_email, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(user_email, websocket)
