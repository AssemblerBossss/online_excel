from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models import User
from backend.app.repository import UserRepository
from backend.app.schemas import SUserInfo


class UserService:

    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session=session)

    async def get_me(self, user: User) -> SUserInfo:
        return SUserInfo.model_validate(user)

    async def get_all_users(self) -> list[SUserInfo]:
        return [SUserInfo.model_validate(t) for t in (await self.user_repo.find_all())]
