import json
import uuid

from redis.asyncio import Redis

from table_service.app.exceptions import InvalidWSTicketException
from table_service.app.schemas import SCurrentUser, SUserFilter, SWsTicketResponse

WS_TICKET_TTL = 30


class WsTicketService:
    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def _key(ticket: str) -> str:
        return f"ws:ticket:{ticket}"

    async def issue(self, current_user: SCurrentUser) -> SWsTicketResponse:
        """Выдать одноразовый тикет, привязанный к пользователю."""
        ticket = uuid.uuid4().hex
        payload = SUserFilter(
            user_id=current_user.user_id,
            email=current_user.email,
            role=current_user.role,
            is_active=current_user.is_active,
        )

        await self.redis.setex(
            self._key(ticket), time=WS_TICKET_TTL, value=payload.model_dump_json()
        )
        return SWsTicketResponse(ticket=ticket, expires_in=WS_TICKET_TTL)

    async def redeem(self, ticket: str) -> SUserFilter:
        """Погасить тикет (одноразово — GETDEL)."""
        raw = await self.redis.getdel(self._key(ticket))
        if not raw:
            raise InvalidWSTicketException()
        return SUserFilter.model_validate(json.loads(raw))
