import logging
from collections.abc import Sequence
from sqlalchemy import delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from auth_service.app.models import User, UserRole

logger = logging.getLogger(__name__)


class UserRepository:
    """Репозиторий для работы с пользователями"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_one_or_none_by_id(self, user_id: int) -> User | None:
        """Найти пользователя по ID"""
        query = select(User).filter_by(id=user_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def find_one_or_none(self, filter_dict: dict) -> User | None:
        """Найти одного пользователя по фильтрам"""
        query = select(User).filter_by(**filter_dict)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        """Найти пользователя по email"""
        query = select(User).filter_by(email=email)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def find_all(self, filters: dict | None = None) -> Sequence[User]:
        """Найти всех пользователей по фильтрам"""
        query = select(User).filter_by(**filters)
        result = (await self._session.execute(query)).scalars().all()
        return result

    async def add(self, new_user: User) -> User:
        """Добавить нового пользователя"""
        self._session.add(new_user)
        await self._session.flush()
        return new_user

    async def add_many(self, users: list[User]) -> Sequence[User]:
        """Добавить нескольких пользователей"""
        self._session.add_all(users)
        await self._session.flush()
        return users

    async def update(self, filters: dict, values: dict) -> int:
        """Обновить пользователей по фильтрам"""
        if not values:
            return 0

        query = (
            update(User)
            .filter_by(**filters)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(query)
        await self._session.flush()
        return result.rowcount

    async def set_avatar(self, user_id: int, object_name: str) -> bool:
        """Сохранить ключ аватара пользователя"""
        return await self.update_by_id(user_id, values={"avatar_url": object_name})

    async def update_by_id(self, user_id: int, values: dict) -> bool:
        """Обновить пользователя по ID"""
        if not values:
            return False

        query = (
            update(User)
            .where(User.id == user_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(query)
        await self._session.flush()
        return result.rowcount > 0

    async def delete(self, filters: dict | None = None) -> int:
        """Удалить пользователей по фильтрам"""
        if not filters:
            return 0

        query = delete(User).filter_by(**filters)
        result = await self._session.execute(query)
        await self._session.flush()
        return result.rowcount

    async def delete_by_id(self, user_id: int) -> bool:
        """Удалить пользователя по ID"""
        query = delete(User).filter_by(id=user_id)
        result = await self._session.execute(query)
        deleted = result.rowcount > 0
        await self._session.flush()
        return deleted

    # AGGREGATION methods
    async def count(self, filters: dict | None = None) -> int:
        """Подсчитать количество пользователей по фильтрам"""
        query = select(func.count()).select_from(User)
        if filters:
            query = query.filter_by(**filters)

        result = await self._session.execute(query)
        return result.scalar()

    async def exists(self, filter_dict: dict | None = None) -> bool:
        """Проверить существование пользователя по фильтрам"""
        query = select(User.id).filter_by(**filter_dict).limit(1)
        result = (await self._session.execute(query)).scalar() is not None
        return result

    async def get_active_users(self) -> Sequence[User]:
        """Получить всех активных пользователей"""
        filter_dict = {"is_active": True}
        return await self.find_all(filters=filter_dict)

    async def get_users_by_role(self, role: UserRole) -> Sequence[User]:
        """Получить пользователей по роли"""
        filters = {"role": role}
        return await self.find_all(filters=filters)

    async def deactivate_user(self, user_id: int) -> bool:
        """Деактивировать пользователя по ID"""
        values = {"is_active": False}
        return await self.update_by_id(user_id, values=values)

    async def change_user_role(self, user_id: int, new_role: UserRole) -> bool:
        """Изменить роль пользователя"""
        values = {"role": new_role}
        return await self.update_by_id(user_id, values=values)
