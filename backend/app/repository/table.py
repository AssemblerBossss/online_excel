from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .base import Base
from backend.app.models import DataTable, User, TableRow, TablePermission, UserRole
from ..exceptions import AccessDeniedException


class TableRepository(Base):

    async def get_table_with_access(self, table_id: int, user_id: int):
        pass

    async def get_table_with_write_access(
        self, table_id: int, user_id: int
    ) -> Optional[DataTable]:
        """
        Получить таблицу только если пользователь имеет права на запись.

        Выполняет двухэтапную проверку:
        1. Находит таблицу по ID (с предзагрузкой permissions)
        2. Проверяет права записи через _check_write_access()

        Args:
            table_id: Идентификатор таблицы для поиска
            user_id: Идентификатор пользователя для проверки прав

        Returns:
            Optional[DataTable]: Объект таблицы с загруженными permissions если доступ есть,
                               None если таблица не найдена

        Raises:
            AccessDeniedException: Если таблица найдена, но у пользователя нет прав на запись

        Note:
            - Использует selectinload для эффективной загрузки связанных permissions
            - Возвращает полноценный объект DataTable готовый к использованию
            - Отличается от get_table_with_access() строгой проверкой именно прав ЗАПИСИ
        """
        async with self._session_scope() as session:
            stmt = (
                select(DataTable)
                .options(selectinload(DataTable.permissions))
                .where(DataTable.id == table_id)
            )

            table = (await session.execute(stmt)).scalar_one_or_none()

            if not table:
                return None

            has_write_access: bool = await self._check_write_access(table, user_id)

            if not has_write_access:
                raise AccessDeniedException
            return table

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
        if table.created_by == user_id:
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
