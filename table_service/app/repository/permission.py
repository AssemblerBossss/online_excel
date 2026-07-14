from collections.abc import Sequence
from sqlalchemy import select, delete, insert, update

from table_service.app.repository.base import Base
from table_service.app.models import TablePermission, UserProjection


class PermissionRepository(Base):
    """Репозиторий для работы с правами доступа к таблицам."""

    async def get_permissions_by_table(
        self, table_id: int
    ) -> Sequence[tuple[TablePermission, str | None]]:
        """Получить все права доступа для таблицы с email-ами пользователей.
        Returns:
            Sequence[tuple[TablePermission, str | None]]:
            Список кортежей (объект права, email пользователя).
            Email может быть None, если пользователь не найден в проекции
        """
        stmt = (
            select(TablePermission, UserProjection.email)
            .outerjoin(UserProjection, UserProjection.id == TablePermission.user_id)
            .where(TablePermission.table_id == table_id)
        )
        result = await self._session.execute(stmt)
        return result.all()  # type: ignore[return-value]

    async def get_permissions(
        self, table_id: int, user_id: int
    ) -> TablePermission | None:
        stmt = select(TablePermission).where(
            TablePermission.table_id == table_id, TablePermission.user_id == user_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_permission(
        self,
        table_id: int,
        user_id: int,
        can_read: bool,
        can_write: bool,
        can_manage: bool,
    ) -> TablePermission:
        stmt = (
            insert(TablePermission)
            .values(
                table_id=table_id,
                user_id=user_id,
                can_read=can_read,
                can_write=can_write,
                can_manage=can_manage,
            )
            .returning(TablePermission)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update_permission(
        self, table_id: int, user_id: int, **fields
    ) -> TablePermission | None:
        stmt = (
            update(TablePermission)
            .where(
                TablePermission.table_id == table_id, TablePermission.user_id == user_id
            )
            .values(**fields)
            .returning(TablePermission)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_permission(self, table_id: int, user_id: int) -> bool:
        stmt = delete(TablePermission).where(
            TablePermission.table_id == table_id,
            TablePermission.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0
