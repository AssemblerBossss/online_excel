from sqlalchemy import select, delete, Sequence, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from table_service.app.repository.base import Base
from table_service.app.models import DataTable


class TableRepository(Base):
    """Репозиторий для работы с таблицами данных (DataTable)."""

    async def get_all_tables(self) -> Sequence[DataTable]:
        """Получить список всех таблиц в базе данных."""
        stmt = select(DataTable).where(not DataTable.is_deleted)
        result = await self._session.execute(stmt)
        tables = result.scalars().all()
        return tables

    async def get_table_by_id(self, table_id: int) -> DataTable | None:
        """Получить таблицу по ее идентификатору."""
        stmt = (
            select(DataTable)
            .options(selectinload(DataTable.permissions))
            .where(DataTable.id == table_id, not DataTable.is_deleted)
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

    async def get_trash(self) -> Sequence[DataTable]:
        """Получить список всех таблиц в корзине."""
        stmt = (
            select(DataTable)
            .where(DataTable.is_deleted)
            .order_by(DataTable.deleted_at.desc())
        )
        result = await self._session.execute(stmt)
        tables = result.scalars().all()
        return tables

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
            .where(DataTable.id == table_id, not DataTable.is_deleted)
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
