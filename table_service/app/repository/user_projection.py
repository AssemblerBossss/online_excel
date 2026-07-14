from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from table_service.app.models import UserProjection


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> UserProjection | None:
        stmt = select(UserProjection).where(UserProjection.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserProjection | None:
        stmt = select(UserProjection).where(UserProjection.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, data: dict):
        user = await self.get_by_id(data["id"])

        if user:
            user.email = data["email"]
            user.role = data["role"]
            user.updated_at = data["timestamp"]
        else:
            user = UserProjection(
                id=data["id"],
                email=data["email"],
                role=data["role"],
                created_at=data["timestamp"],
                is_active=True,
            )
            self.session.add(user)

        await self.session.commit()

    async def mark_deleted(self, user_id: int):
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = False
            await self.session.commit()
