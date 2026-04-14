from typing import Callable, Coroutine, Any
from sqlalchemy import select, delete, Sequence
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.sync import update

from table_service.app.repository.base import Base
from table_service.app.models import DataTable
from table_service.app.exceptions import AccessDeniedException


class TableRepository(Base):
    """Репозиторий для работы с таблицами данных (DataTable)."""

    async def get_all_tables(self) -> Sequence[DataTable]:
        """
        Получить список всех таблиц в базе данных.

        Returns:
            List[DataTable]: Список всех таблиц. Если таблиц нет — возвращает пустой список.
        """
        stmt = select(DataTable)
        result = await self._session.execute(stmt)
        tables = result.scalars().all()
        return tables

    async def _get_table_with_access_check(
        self,
        table_id: int,
        user_id: int,
        user_role: str,
        access_checker: Callable[[DataTable, int, str], Coroutine[Any, Any, bool]],
    ) -> DataTable | None:
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
        stmt = (
            select(DataTable)
            .options(selectinload(DataTable.permissions))
            .where(DataTable.id == table_id)
        )

        result = await self._session.execute(stmt)
        table = result.scalar_one_or_none()

        if not table:
            return None

        has_access = await access_checker(table, user_id, user_role)

        if not has_access:
            raise AccessDeniedException

        return table

    async def get_table_with_read_access(
        self, table_id: int, user_id: int, user_role: str
    ) -> DataTable | None:
        """
        Получить таблицу с проверкой прав на чтение.

        Args:
            table_id: ID таблицы
            user_id: ID пользователя
            user_role: Роль пользователя

        Returns:
            Optional[DataTable]: Таблица, если пользователь имеет доступ на чтение.
        """
        return await self._get_table_with_access_check(
            table_id, user_id, user_role, self._check_read_access
        )

    async def get_table_with_write_access(
        self, table_id: int, user_id: int, user_role: str = None
    ) -> DataTable | None:
        """
        Получить таблицу с проверкой прав на запись.

        Args:
            table_id: ID таблицы
            user_id: ID пользователя
            user_role: Роль пользователя
        Returns:
            Optional[DataTable]: Таблица, если пользователь имеет доступ на запись.
        """
        return await self._get_table_with_access_check(
            table_id, user_id, user_role, self._check_write_access
        )

    async def _check_read_access(
        self, table: DataTable, user_id: int, user_role: str = None
    ) -> bool:
        """
        Упрощенная проверка прав на чтение:
        - Любой аутентифицированный пользователь может читать любую таблицу
        """
        return user_id is not None

    async def _check_write_access(
        self, table: DataTable, user_id: int, user_role: str = None
    ) -> bool:
        """
        Проверить права на запись для пользователя в указанной таблице.

        Иерархия проверки прав (в порядке приоритета):
        1. Владелец таблицы (created_by) - всегда имеет полный доступ
        2. Администратор системы (ADMIN) - всегда имеет полный доступ
        3. Пользователь с явными правами в table_permissions (can_write или can_manage)
        4. Публичные таблицы (is_public=True) - запись запрещена (только чтение)
        5. Во всех остальных случаях - доступ запрещен

        Args:
            table: Объект таблицы DataTable с загруженными permissions
            user_id: Идентификатор пользователя для проверки прав
            user_role: Роль пользователя

        Returns:
            bool: True если пользователь имеет права на запись, иначе False

        Note:
            - Метод не проверяет существование таблицы (предполагается валидная table)
            - Метод ожидает что permissions уже загружены через selectinload/joinedload
            - Для публичных таблиц всегда возвращает False (только чтение)
        """
        if table.created_by_id == user_id:
            return True

        if user_role and user_role.upper() == "ADMIN":
            return True

        for permission in table.permissions:
            if permission.user_id == user_id:
                if permission.can_write or permission.can_manage:
                    return True
        if table.is_public:
            return False

        return False

    async def create_table(self, table_data: dict, user_id: int) -> DataTable:
        """
        Создать новую таблицу данных.
        Args:
            table_data: Данные для создания таблицы (имя, описание, схема и т.д.)
            user_id: Идентификатор пользователя, создающего таблицу.
        """
        stmt = (
            insert(DataTable)
            .values(
                name=table_data.get("name"),
                description=table_data.get("description"),
                is_public=table_data.get("is_public"),
                columns_schema=table_data.get("columns_schema"),
                created_by_id=user_id,
            )
            .returning(DataTable)
        )

        result = await self._session.execute(stmt)
        table = result.scalar_one()
        await self._session.refresh(table)

        return table

    async def update_table(self, table_id: int, data: dict) -> DataTable | None:
        """Обновить таблицу"""
        stmt = (
            update(DataTable)
            .where(DataTable.id == table_id)
            .values(**data)
            .returning(DataTable)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_table(self, table_id: int, user_id: int, user_role: str) -> bool:
        """
        Удалить таблицу со всеми данными.

        Благодаря cascade="all, delete-orphan" в модели DataTable,
        при удалении таблицы автоматически удалятся:
        - Все строки таблицы (TableRow)
        - Все права доступа (TablePermission)

        Args:
            table_id: ID таблицы для удаления
            user_id: ID пользователя (для проверки прав)
            user_role: Роль пользователя

        Returns:
            bool: True если таблица удалена, False если не найдена

        Raises:
            AccessDeniedException: Если нет прав на удаление
        """

        table = await self.get_table_with_write_access(
            table_id=table_id, user_id=user_id, user_role=user_role
        )

        if not table:
            return False

        stmt = delete(DataTable).where(DataTable.id == table_id)
        result = await self._session.execute(stmt)

        return result.rowcount > 0
