from sqlalchemy import select, delete, Sequence, update, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from table_service.app.repository.base import Base
from table_service.app.models import DataTable, TablePermission


class TableRepository(Base):
    """Репозиторий для работы с таблицами данных (DataTable)."""

    async def get_all_tables(self, user_id: int, user_role: str) -> Sequence[DataTable]:
        """Таблицы, видимые пользователю: свои + публичные + с выданным can_read. Admin — все."""
        stmt = select(DataTable).where(DataTable.is_deleted.is_(False))
        if not (user_role and user_role.upper() == "ADMIN"):
            stmt = stmt.where(
                or_(
                    DataTable.created_by_id == user_id,
                    DataTable.is_public.is_(True),
                    DataTable.id.in_(
                        select(TablePermission.table_id).where(
                            TablePermission.user_id == user_id,
                            TablePermission.can_read.is_(True),
                        )
                    ),
                )
            )
        result = await self._session.execute(stmt)
        tables = result.scalars().all()
        return tables

    async def get_table_by_id(self, table_id: int) -> DataTable | None:
        """Получить таблицу по ее идентификатору."""
        stmt = (
            select(DataTable)
            .options(selectinload(DataTable.permissions))
            .where(DataTable.id == table_id, DataTable.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_deleted_table_by_id(self, table_id: int) -> DataTable | None:
        """Получить удалённую таблицу по ID (только из корзины)."""
        stmt = (
            select(DataTable)
            .options(selectinload(DataTable.permissions))
            .where(DataTable.id == table_id, DataTable.is_deleted)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_trash(self, user_id: int, user_role: str) -> Sequence[DataTable]:
        """Корзина: свои таблицы + те, где есть can_manage. Admin — все."""
        stmt = select(DataTable).where(DataTable.is_deleted)
        if not (user_role and user_role.upper() == "ADMIN"):
            stmt = stmt.where(
                or_(
                    DataTable.created_by_id == user_id,
                    DataTable.id.in_(
                        select(TablePermission.table_id).where(
                            TablePermission.user_id == user_id,
                            TablePermission.can_manage.is_(True),
                        )
                    ),
                )
            )
        stmt = stmt.order_by(DataTable.deleted_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create_table(self, table_data: dict, user_id: int) -> DataTable:
        """Создать новую таблицу данных."""
        stmt = (
            insert(DataTable)
            .values(
                name=table_data.get("name"),
                description=table_data.get("description"),
                is_public=table_data.get("is_public"),
                columns_schema=table_data.get("columns_schema"),
                created_by_id=user_id,
                is_deleted=False,
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
            .where(DataTable.id == table_id, DataTable.is_deleted.is_(False))
            .values(**data)
            .returning(DataTable)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_table(self, table_id: int) -> bool:
        """
        Удалить таблицу со всеми данными.

        Благодаря cascade="all, delete-orphan" в модели DataTable,
        при удалении таблицы автоматически удалятся:
        - Все строки таблицы (TableRow)
        - Все права доступа (TablePermission)
        """
        stmt = delete(DataTable).where(DataTable.id == table_id, DataTable.is_deleted)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_table(self, table_id: int) -> bool:
        """
        Мягкое удаление.
        Помечает строки удаленными,
        но не удаляет совсем.
        """
        stmt = (
            update(DataTable)
            .where(DataTable.id == table_id)
            .values(is_deleted=True, deleted_at=datetime.now(timezone.utc))
        ).returning(DataTable.id)

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def restore_table(self, table_id: int) -> DataTable | None:
        """Восстановление таблицы из 'корзины'."""
        stmt = (
            update(DataTable)
            .where(DataTable.id == table_id)
            .values(is_deleted=False, deleted_at=None)
            .returning(DataTable)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
