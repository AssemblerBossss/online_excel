from contextlib import asynccontextmanager
from sqlalchemy import select, update, delete, insert
from typing import Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core import AsyncSessionFactory

from backend.app.models import TableRow, DataTable


class DataRepository:

    def __init__(self):
        self.session_factory = AsyncSessionFactory

    @asynccontextmanager
    async def _session_scope(self) -> AsyncSession:
        """Context manager for handling database sessions.

        Provides automatic transaction management with commit/rollback
        and proper session cleanup.
        """
        async with self.session_factory() as session:
            try:
                session.expire_on_commit = False
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_rows_by_table_id(
            self,
            table_id: int,
            skip: int = 0,
            limit: int = 100,
            sort_by: Optional[str] = None,
            sort_order: Optional[str] = "asc",
    ) -> List[TableRow]:

        async with self._session_scope() as session:
            if sort_order.lower() == "desc":
                stmt = select(TableRow).where(TableRow.table_id == table_id).limit(limit).offset(skip).order_by(sort_by)
            else:
                stmt = select(TableRow).where(TableRow.table_id == table_id).limit(limit).offset(skip).order_by(sort_by)



    # async def _get_task(self, *filters: Any) -> Optional[Task]:
    #     """Generic method to retrieve a single task matching given filters.
    #
    #     Args:
    #         *filters: SQLAlchemy filter conditions
    #
    #     Returns:
    #         Optional[Task]: Task object if found, None otherwise
    #     """
    #     async with self._session_scope() as session:
    #         stmt = select(Task).where(*filters)
    #         return (await session.scalars(stmt)).one_or_none()
    #
    #
    # async def get_user_task(self, task_id: UUID, user_id: UUID) -> Optional[Task]:
    #     """Retrieve a specific task belonging to a particular user.
    #
    #     Args:
    #         task_id: UUID of the task to find
    #         user_id: ID of the user
    #
    #     Returns:
    #         Optional[Task]: Task object if found and belongs to user, None otherwise
    #     """
    #     return await self._get_task(Task.task_id == task_id, Task.user_id == user_id)
    #
    # async def get_user_tasks(self, user_id: UUID) -> list[Task]:
    #     """Retrieve all users tasks from the database.
    #
    #     Args:
    #         user_id: ID of the user
    #
    #     Returns:
    #         list[Task]: List of all tasks
    #     """
    #     async with self._session_scope() as session:
    #         stmt = select(Task).where(Task.user_id == user_id)
    #         return (await session.scalars(stmt)).all()
    #
    # async def get_tasks_by_category(self, category_name: str) -> list[Task]:
    #     """Retrieve all tasks belonging to a specific category.
    #
    #     Args:
    #         category_name: Name of the category to filter by
    #
    #     Returns:
    #         list[Task]: List of tasks in the specified category
    #     """
    #     async with self._session_scope() as session:
    #         stmt = (
    #             select(Task)
    #             .join(Category, Task.category_id == Category.category_id)
    #             .where(Category.name == category_name)
    #         )
    #         return (await session.scalars(stmt)).all()
    #
    # async def create_task(self, task: TaskCreate, user_id: UUID) -> UUID:
    #     """Retrieve all tasks from the database.
    #
    #     Returns:
    #         list[Task]: List of all tasks
    #     """
    #     async with self._session_scope() as session:
    #         task_model = Task(
    #             name=task.name,
    #             pomodoro_count=task.pomodoro_count,
    #             category_id=task.category_id,
    #             user_id=user_id,
    #         )
    #
    #         session.add(task_model)
    #         await session.flush()
    #         return task_model.task_id
    #
    # async def delete_task(self, task_id: UUID, user_id: UUID) -> None:
    #     """Retrieve all tasks from the database.
    #
    #     Returns:
    #         list[Task]: List of all tasks
    #     """
    #     async with self._session_scope() as session:
    #         stmt = delete(Task).where(Task.task_id == task_id, Task.user_id == user_id)
    #         await session.execute(stmt)
    #
    # async def update_task(self, task_update: TaskUpdate) -> Task:
    #     """Retrieve all tasks from the database.
    #
    #     Returns:
    #         list[Task]: List of all tasks
    #     """
    #     async with self._session_scope() as session:
    #         stmt = (
    #             update(Task)
    #             .where(Task.task_id == task_update.task_id)
    #             .values(
    #                 name=task_update.name,
    #                 category_id=task_update.category_id,
    #                 pomodoro_count=task_update.pomodoro_count,
    #             )
    #             .returning(Task)
    #         )
    #         return (await session.scalars(stmt)).one_or_none()
