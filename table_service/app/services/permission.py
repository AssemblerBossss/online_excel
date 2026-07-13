import logging

from table_service.app.exceptions import (
    NotFoundException,
    AccessDeniedException,
    PermissionAlreadyExistsException,
    CanNotCreatePermissionException,
)
from table_service.app.models import DataTable, TablePermission
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.schemas import TablePermissionResponse, TablePermissionCreate

logger = logging.getLogger(__name__)


class PermissionService:
    ADMIN_ROLE = "ADMIN"

    @staticmethod
    def _to_response(permission) -> TablePermissionResponse:
        return TablePermissionResponse(
            id=permission.id,
            user_id=permission.user_id,
            table_id=permission.table_id,
            can_read=permission.can_read,
            can_write=permission.can_write,
            can_manage=permission.can_manage,
            created_at=permission.created_at,
        )

    async def get_table_with_read_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        table = await uow_session.tables.get_table_by_id(table_id=table_id)
        if not table:
            raise NotFoundException("Таблица не найдена")
        if not await self.check_read_access(
            uow_session=uow_session, table=table, user_id=user_id, user_role=user_role
        ):
            raise AccessDeniedException()
        return table

    async def get_table_with_write_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        table = await uow_session.tables.get_table_by_id(table_id=table_id)
        if not table:
            raise NotFoundException("Таблица не найдена")
        if not await self.check_write_access(
            uow_session=uow_session, table=table, user_id=user_id, user_role=user_role
        ):
            logger.warning("User %s denied write access to table %s", user_id, table_id)
            raise AccessDeniedException()
        return table

    async def _check_table_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> None:
        """Проверить доступ пользователя к таблице."""
        table = await uow_session.tables.get_table_by_id(table_id=table_id)
        if not table:
            raise NotFoundException("Таблица не найдена")

        is_owner = table.created_by_id == user_id
        is_admin = user_role and user_role.upper() == self.ADMIN_ROLE

        if not (is_owner or is_admin):
            raise AccessDeniedException()

    async def check_read_access(
        self, uow_session: UnitOfWork, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверить, имеет ли пользователь право на чтение таблицы."""
        if table.created_by_id == user_id:
            return True
        if user_role and user_role.upper() == self.ADMIN_ROLE:
            return True
        if table.is_public:
            return True
        perm: TablePermission | None = await uow_session.permissions.get_permissions(
            table_id=table.id, user_id=user_id
        )
        if perm and perm.can_read:
            return True
        return False

    async def check_write_access(
        self, uow_session: UnitOfWork, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверить, имеет ли пользователь право на запись в таблицу."""
        if table.created_by_id == user_id:
            return True
        if user_role and user_role.upper() == self.ADMIN_ROLE:
            return True
        perm: TablePermission | None = await uow_session.permissions.get_permissions(
            table_id=table.id, user_id=user_id
        )
        if perm and (perm.can_write or perm.can_manage):
            return True
        return False

    async def check_manage_access(
        self, uow_session: UnitOfWork, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверить, имеет ли пользователь право на управление (изменение прав, удаление таблицы)."""
        if table.created_by_id == user_id:
            return True
        if user_role and user_role.upper() == self.ADMIN_ROLE:
            return True
        perm: TablePermission = await uow_session.permissions.get_permissions(
            table_id=table.id, user_id=user_id
        )
        if perm and perm.can_manage:
            return True
        return False

    async def get_permissions(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> list[TablePermissionResponse]:
        """Получить список всех прав доступа для указанной таблицы."""
        async with uow_session.start():
            await self._check_table_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            perms = await uow_session.permissions.get_permissions_by_table(
                table_id=table_id
            )
            return [self._to_response(p) for p in perms]

    async def create_permission(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        data: TablePermissionCreate,
    ) -> TablePermissionResponse:
        """Создать новое право доступа для пользователя на указанную таблицу."""
        async with uow_session.start():
            await self._check_table_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            if await uow_session.permissions.get_permissions(
                table_id=table_id, user_id=user_id
            ):
                raise PermissionAlreadyExistsException()

            if not (
                perm := await uow_session.permissions.create_permission(
                    table_id=table_id,
                    user_id=user_id,
                    can_read=data.can_read,
                    can_write=data.can_write,
                    can_manage=data.can_manage,
                )
            ):
                raise CanNotCreatePermissionException()
            logger.info(
                "Successfully created permission %s for user %s on table %s",
                perm.id,
                data.user_id,
                table_id,
            )
            return self._to_response(perm)

    async def delete_permission(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        target_user_id: int,
        user_id: int,
        user_role: str,
    ) -> None:
        async with uow_session.start():
            await self._check_table_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            if not (
                await uow_session.permissions.delete_permission(
                    table_id=table_id, user_id=target_user_id
                )
            ):
                raise NotFoundException("Права для данного пользователя не найдены")

            logger.info(
                "User %s revoked permissions on table %s from user %s",
                user_id,
                table_id,
                target_user_id,
            )
