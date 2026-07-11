from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from chat_service.app.models import ChatUser


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: int):
        result = await self._session.execute(
            select(ChatUser).where(ChatUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, data: dict):
        user = await self.get_by_id(data["id"])
        if user:
            user.email = data["email"]
            user.updated_at = data["timestamp"]
        else:
            user = ChatUser(
                id=data["id"],
                email=data["email"],
                role=data["role"],
                created_at=data["timestamp"],
                is_active=True,
            )
            self._session.add(user)
        await self._session.commit()

    async def mark_deleted(self, user_id: int):
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = False
            await self._session.commit()
