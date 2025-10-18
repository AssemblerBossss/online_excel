from sqlalchemy import delete, func, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from typing import Optional, List

from backend.app.models import User
from backend.app.schemas import UserFilter, UserBase, UserUpdate
from backend.app.models import UserRole





from loguru import logger

class UserRepository:
    """Репозиторий для работы с пользователями"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self.model = User

    async def find_one_or_none_by_id(self, user_id: int) -> Optional["User"]:
        """
        Найти пользователя по ID

        Args:
            user_id: ID пользователя

        Returns:
            User или None если не найден
        """
        try:
            query = select(User).filter_by(id=user_id)
            result = await self._session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                logger.info(f"Пользователь с ID {user_id} найден")
            else:
                logger.info(f"Пользователь с ID {user_id} не найден")

            return user
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске пользователя с ID {user_id}: {e}")
            raise

    async def find_one_or_none(self, filters: UserFilter) -> Optional["User"]:
        """
        Найти одного пользователя по фильтрам

        Args:
            filters: Фильтры для поиска

        Returns:
            User или None если не найден
        """
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.debug(f"Поиск пользователя по фильтрам: {filter_dict}")

        try:
            query = select(User).filter_by(**filter_dict)
            result = await self._session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                logger.info(f"Пользователь найден по фильтрам: {filter_dict}")
            else:
                logger.info(f"Пользователь не найден по фильтрам: {filter_dict}")

            return user
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске пользователя по фильтрам {filter_dict}: {e}")
            raise

    async def find_by_email(self, email: str) -> Optional["User"]:
        """
        Найти пользователя по email

        Args:
            email: Email пользователя

        Returns:
            User или None если не найден
        """
        try:
            query = select(User).filter_by(email=email)
            result = await self._session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                logger.info(f"Пользователь с email {email} найден")
            else:
                logger.info(f"Пользователь с email {email} не найден")

            return user
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске пользователя по email {email}: {e}")
            raise

    async def find_all(self, filters: Optional[UserFilter] = None) -> List["User"]:
        """
        Найти всех пользователей по фильтрам

        Args:
            filters: Фильтры для поиска (опционально)

        Returns:
            Список пользователей
        """
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        logger.debug(f"Поиск всех пользователей по фильтрам: {filter_dict}")

        try:
            query = select(User).filter_by(**filter_dict)
            result = await self._session.execute(query)
            users = result.scalars().all()

            logger.info(f"Найдено {len(users)} пользователей")

            return users
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске всех пользователей по фильтрам {filter_dict}: {e}")
            raise

    async def add(self, user_data: UserBase) -> "User":
        """
        Добавить нового пользователя

        Args:
            user_data: Данные пользователя

        Returns:
            Созданный пользователь
        """
        values_dict = user_data.model_dump(exclude_unset=True)
        logger.debug(f"Добавление пользователя с параметрами: {values_dict}")

        try:
            new_user = User(**values_dict)
            self._session.add(new_user)
            await self._session.flush()

            logger.info(f"Пользователь {new_user.email} успешно добавлен с ID {new_user.id}")

            return new_user
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")
            raise

    async def add_many(self, users_data: List[UserBase]) -> List["User"]:
        """
        Добавить нескольких пользователей

        Args:
            users_data: Список данных пользователей

        Returns:
            Список созданных пользователей
        """
        values_list = [user.model_dump(exclude_unset=True) for user in users_data]
        logger.info(f"Добавление {len(values_list)} пользователей")

        try:
            new_users = [User(**values) for values in values_list]
            self._session.add_all(new_users)
            await self._session.flush()

            logger.success(f"Успешно добавлено {len(new_users)} пользователей")

            return new_users
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при добавлении нескольких пользователей: {e}")
            raise

    async def update(self, filters: UserFilter, update_data: UserUpdate) -> int:
        """
        Обновить пользователей по фильтрам

        Args:
            filters: Фильтры для выбора пользователей
            update_data: Данные для обновления

        Returns:
            Количество обновленных записей
        """
        filter_dict = filters.model_dump(exclude_unset=True)
        update_dict = update_data.model_dump(exclude_unset=True)

        if not update_dict:
            logger.warning("Нет данных для обновления")
            return 0

        logger.debug(f"Обновление пользователей по фильтру: {filter_dict} с параметрами: {update_dict}")

        try:
            query = (
                update(User)
                .where(*[getattr(User, k) == v for k, v in filter_dict.items()])
                .values(**update_dict)
                .execution_options(synchronize_session="fetch")
            )
            result = await self._session.execute(query)

            logger.info(f"Обновлено {result.rowcount} пользователей")
            await self._session.flush()

            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при обновлении пользователей: {e}")
            raise

    async def update_by_id(self, user_id: int, update_data: UserUpdate) -> bool:
        """
        Обновить пользователя по ID

        Args:
            user_id: ID пользователя
            update_data: Данные для обновления

        Returns:
            True если пользователь обновлен, False если не найден
        """
        update_dict = update_data.model_dump(exclude_unset=True)

        if not update_dict:
            logger.warning("Нет данных для обновления")
            return False

        logger.debug(f"Обновление пользователя с ID {user_id} с параметрами: {update_dict}")

        try:
            query = (
                update(User)
                .where(User.id == user_id)
                .values(**update_dict)
                .execution_options(synchronize_session="fetch")
            )
            result = await self._session.execute(query)

            updated = result.rowcount > 0
            if updated:
                logger.info(f"Пользователь с ID {user_id} успешно обновлен")
            else:
                logger.warning(f"Пользователь с ID {user_id} не найден для обновления")

            await self._session.flush()

            return updated
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при обновлении пользователя с ID {user_id}: {e}")
            raise

    async def delete(self, filters: UserFilter) -> int:
        """
        Удалить пользователей по фильтрам

        Args:
            filters: Фильтры для удаления

        Returns:
            Количество удаленных записей
        """
        filter_dict = filters.model_dump(exclude_unset=True)

        if not filter_dict:
            logger.error("Нужен хотя бы один фильтр для удаления")
            raise ValueError("Нужен хотя бы один фильтр для удаления")

        logger.warning(f"Удаление пользователей по фильтру: {filter_dict}")

        try:
            query = delete(User).filter_by(**filter_dict)
            result = await self._session.execute(query)

            logger.info(f"Удалено {result.rowcount} пользователей")
            await self._session.flush()

            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при удалении пользователей: {e}")
            raise

    async def delete_by_id(self, user_id: int) -> bool:
        """
        Удалить пользователя по ID

        Args:
            user_id: ID пользователя

        Returns:
            True если пользователь удален, False если не найден
        """
        logger.warning(f"Удаление пользователя с ID {user_id}")

        try:
            query = delete(User).filter_by(id=user_id)
            result = await self._session.execute(query)

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Пользователь с ID {user_id} успешно удален")
            else:
                logger.warning(f"Пользователь с ID {user_id} не найден для удаления")

            await self._session.flush()

            return deleted
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при удалении пользователя с ID {user_id}: {e}")
            raise

    async def count(self, filters: Optional[UserFilter] = None) -> int:
        """
        Подсчитать количество пользователей по фильтрам

        Args:
            filters: Фильтры для подсчета (опционально)

        Returns:
            Количество пользователей
        """
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        logger.debug(f"Подсчет количества пользователей по фильтру: {filter_dict}")

        try:
            query = select(func.count(User.id)).filter_by(**filter_dict)
            result = await self._session.execute(query)
            count = result.scalar()

            logger.info(f"Найдено {count} пользователей")

            return count
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при подсчете пользователей: {e}")
            raise

    async def exists(self, filters: UserFilter) -> bool:
        """
        Проверить существование пользователя по фильтрам

        Args:
            filters: Фильтры для проверки

        Returns:
            True если пользователь существует, False если нет
        """
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.debug(f"Проверка существования пользователя по фильтрам: {filter_dict}")

        try:
            query = select(User.id).filter_by(**filter_dict).limit(1)
            result = await self._session.execute(query)
            exists = result.scalar() is not None

            if exists:
                logger.debug(f"Пользователь существует по фильтрам: {filter_dict}")
            else:
                logger.debug(f"Пользователь не существует по фильтрам: {filter_dict}")

            return exists
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при проверке существования пользователя: {e}")
            raise

    async def get_active_users(self) -> List["User"]:
        """
        Получить всех активных пользователей

        Returns:
            Список активных пользователей
        """
        logger.debug("Получение списка активных пользователей")
        return await self.find_all(UserFilter(is_active=True))

    async def get_users_by_role(self, role: UserRole) -> List["User"]:
        """
        Получить пользователей по роли

        Args:
            role: Роль пользователя

        Returns:
            Список пользователей с указанной ролью
        """
        logger.debug(f"Получение пользователей с ролью {role}")
        return await self.find_all(UserFilter(role=role))

    async def deactivate_user(self, user_id: int) -> bool:
        """
        Деактивировать пользователя по ID

        Args:
            user_id: ID пользователя

        Returns:
            True если пользователь деактивирован, False если не найден
        """
        logger.warning(f"Деактивация пользователя с ID {user_id}")
        return await self.update_by_id(user_id, UserUpdate(is_active=False))

    async def change_user_role(self, user_id: int, new_role: UserRole) -> bool:
        """
        Изменить роль пользователя

        Args:
            user_id: ID пользователя
            new_role: Новая роль пользователя

        Returns:
            True если роль изменена, False если пользователь не найден
        """
        logger.info(f"Изменение роли пользователя {user_id} на {new_role}")
        return await self.update_by_id(user_id, UserUpdate(role=new_role))
