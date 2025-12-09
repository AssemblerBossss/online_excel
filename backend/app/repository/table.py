from typing import Optional, Callable, Coroutine, Any, List
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from backend.app.repository.base import Base
from backend.app.models import DataTable, User, UserRole
from backend.app.exceptions import AccessDeniedException
from backend.app.schemas import DataTableCreate


class TableRepository(Base):
    """Репозиторий для работы с таблицами данных (DataTable)."""

    async def get_all_tables(self) -> List[DataTable]:
        """
        Получить список всех таблиц в базе данных.

        Returns:
            List[DataTable]: Список всех таблиц. Если таблиц нет — возвращает пустой список.
        """
        async with self._session_scope() as session:
            stmt = select(DataTable)
            tables: List[DataTable] = (await session.scalars(stmt)).all()
            return tables

    async def _get_table_with_access_check(
        self,
        table_id: int,
        user_id: int,
        access_checker: Callable[[DataTable, int], Coroutine[Any, Any, bool]],
    ) -> Optional[DataTable]:
        """
        Базовая логика получения таблицы с проверкой прав доступа.

        Args:
            table_id: ID таблицы
            user_id: ID пользователя
            access_checker: Функция проверки прав доступа

        Returns:
            Optional[DataTable]: Таблица если доступ есть, иначе None

        Raises:
            AccessDeniedException: Если нет прав доступа
        """
        async with self._session_scope() as session:
            stmt = (
                select(DataTable)
                .options(selectinload(DataTable.permissions))
                .where(DataTable.id == table_id)
            )

            table = (await session.scalars(stmt)).one_or_none()

            if not table:
                return None

            has_access = await access_checker(table, user_id)

            if not has_access:
                raise AccessDeniedException
            return table

    async def get_table_with_read_access(
        self, table_id: int, user_id: int
    ) -> Optional[DataTable]:
        """
        Получить таблицу с проверкой прав на чтение.

        Args:
            table_id: ID таблицы
            user_id: ID пользователя

        Returns:
            Optional[DataTable]: Таблица, если пользователь имеет доступ на чтение.
        """
        return await self._get_table_with_access_check(
            table_id, user_id, self._check_read_access
        )

    async def get_table_with_write_access(
        self, table_id: int, user_id: int
    ) -> Optional[DataTable]:
        """
        Получить таблицу с проверкой прав на запись.

        Args:
            table_id: ID таблицы
            user_id: ID пользователя

        Returns:
            Optional[DataTable]: Таблица, если пользователь имеет доступ на запись.
        """
        return await self._get_table_with_access_check(
            table_id, user_id, self._check_write_access
        )

    async def _check_read_access(self, table: DataTable, user_id: int) -> bool:
        """
        Упрощенная проверка прав на чтение:
        - Любой аутентифицированный пользователь может читать любую таблицу
        """
        return user_id is not None

    async def _check_write_access(self, table: DataTable, user_id: int) -> bool:
        """
        Проверить права на запись для пользователя в указанной таблице.

        Иерархия проверки прав (в порядке приоритета):
        1. Владелец таблицы (created_by) - всегда имеет полный доступ
        2. Администратор системы (UserRole.ADMIN) - всегда имеет полный доступ
        3. Пользователь с явными правами в table_permissions (can_write или can_manage)
        4. Публичные таблицы (is_public=True) - запись запрещена (только чтение)
        5. Во всех остальных случаях - доступ запрещен

        Args:
            table: Объект таблицы DataTable с загруженными permissions
            user_id: Идентификатор пользователя для проверки прав

        Returns:
            bool: True если пользователь имеет права на запись, иначе False

        Note:
            - Метод не проверяет существование таблицы (предполагается валидная table)
            - Метод ожидает что permissions уже загружены через selectinload/joinedload
            - Для публичных таблиц всегда возвращает False (только чтение)
        """
        if table.created_by_id == user_id:
            return True

        async with self._session_scope() as session:
            stmt = select(User).where(User.id == user_id)
            user: Optional[User] = (await session.scalars(stmt)).one_or_none()

            if user and user.role == UserRole.ADMIN:
                return True

            for permission in table.permissions:
                if permission.user_id == user_id:
                    if permission.can_write or permission.can_manage:
                        return True

            if table.is_public:
                return False

            return False

    async def create_table(
        self, table_data: DataTableCreate, user_id: int
    ) -> DataTable:
        """
        Создать новую таблицу данных.

        Args:
            table_data: Данные для создания таблицы (имя, описание, схема и т.д.)
            user_id: Идентификатор пользователя, создающего таблицу.

        Returns:
            DataTable: Созданная таблица с подгруженным владельцем.
        """
        async with self._session_scope() as session:
            stmt = (
                insert(DataTable)
                .values(
                    name=table_data.name,
                    description=table_data.description,
                    is_public=table_data.is_public,
                    columns_schema=table_data.columns_schema,
                    created_by_id=user_id,
                )
                .returning(DataTable)
            )

            table = (await session.scalars(stmt)).one_or_none()
            await session.refresh(table, ["created_by"])
            return table

    async def delete_table(self, table_id: int, user_id: int) -> None:
        pass
