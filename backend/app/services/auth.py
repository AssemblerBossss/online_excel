from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.exceptions import UserAlreadyExistsException
from backend.app.repository import UserRepository
from backend.app.schemas import SUserRegister, SUserFilter, SUserAddDB, SUserInfo
from backend.app.utils import get_password_hash


class AuthService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register_user(self, user_data: SUserRegister) -> None:
        existing_user = await self.user_repo.find_one_or_none(
            filters=SUserFilter(email=user_data.email)
        )
        if existing_user:
            raise UserAlreadyExistsException

        hashed_password = get_password_hash(user_data.password)

        # Подготовка данных для добавления
        user_data_dict = user_data.model_dump()
        user_data_dict.pop("confirm_password", None)
        user_data_dict.pop("password", None)
        user_data_dict["hashed_password"] = hashed_password  # Заменяем на хеш

        await self.user_repo.add(user_data=SUserAddDB(**user_data_dict))
