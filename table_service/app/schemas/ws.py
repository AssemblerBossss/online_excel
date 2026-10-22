from pydantic import BaseModel


class SWsTicketResponse(BaseModel):
    """Одноразовый тикет для WebSocket-подключения."""

    ticket: str
    expires_in: int
