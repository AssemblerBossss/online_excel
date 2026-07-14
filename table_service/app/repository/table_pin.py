from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from table_service.app.repository.base import Base
from table_service.app.models import TablePin


class TablePinRepository(Base):
    """Репозиторий закрепленных пользователем страниц"""

    async def get_pinned_tables_ids(self, user_id: int) -> set[int]:
        stmt = select(TablePin.table_id).where(TablePin.user_id == user_id)
        result = await self._session.execute(statement=stmt)
        return set(result.scalars().all())

    async def pin(self, user_id: int, table_id: int) -> None:
        """
        Закрепить таблицу. ON CONFLICT DO NOTHING — идемпотентно:
        повторный вызов не упадёт и не создаст дубликат
        (UniqueConstraint уже защищает на уровне БД).
        """
        stmt = (
            insert(TablePin)
            .values(user_id=user_id, table_id=table_id)
            .on_conflict_do_nothing(constraint="uq_table_pins_user_table")
        )

        await self._session.execute(stmt)

    async def unpin(self, user_id: int, table_id: int) -> bool:
        """Открепить таблицу. Возвращает True, если запись реально была удалена."""
        stmt = delete(TablePin).where(
            TablePin.user_id == user_id, TablePin.table_id == table_id
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0
