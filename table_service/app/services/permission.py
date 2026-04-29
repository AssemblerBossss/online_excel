import logging

from table_service.app.exceptions import (
    NotFoundException,
    AccessDeniedException,
    PermissionAlreadyExistsException,
    CanNotCreatePermissionException,
)
from table_service.app.models import DataTable, TablePermission
from table_service.app.repository import TableRepository, PermissionRepository
from table_service.app.schemas import TablePermissionResponse, TablePermissionCreate

logger = logging.getLogger(__name__)


class PermissionService:

    ADMIN_ROLE = "ADMIN"

    def __init__(
        self,
        table_repo: TableRepository,
        permission_repo: PermissionRepository,
    ):
        self.table_repo = table_repo
        self.permission_repo = permission_repo

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

    async def _check_table_access(
        self, table_id: int, user_id: int, user_role: str
    ) -> None:
        """Проверить доступ пользователя к таблице."""
        table: DataTable = await self.table_repo.get_table_by_id(table_id=table_id)
        if not table:
            raise NotFoundException("Таблица не найдена")

        is_owner = table.created_by_id == user_id
        is_admin = user_role and user_role.upper() == self.ADMIN_ROLE

        if not (is_owner or is_admin):
            raise AccessDeniedException()

    async def check_read_access(
        self, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверить, имеет ли пользователь право на чтение таблицы."""
        if table.created_by_id == user_id:
            return True
        if user_role and user_role.upper() == self.ADMIN_ROLE:
            return True
        if table.is_public:
            return True
        perm: TablePermission = await self.permission_repo.get_permissions(
            table_id=table.id, user_id=user_id
        )
        if perm and perm.can_read:
            return True
        return False

    async def check_write_access(
        self, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверить, имеет ли пользователь право на запись в таблицу."""
        if table.created_by_id == user_id:
            return True
        if user_role and user_role.upper() == self.ADMIN_ROLE:
            return True
        perm: TablePermission = await self.permission_repo.get_permissions(
            table_id=table.id, user_id=user_id
        )
        if perm and (perm.can_write or perm.can_manage):
            return True
        return False

    async def check_manage_access(
        self, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверить, имеет ли пользователь право на управление (изменение прав, удаление таблицы)."""
        if table.created_by_id == user_id:
            return True
        if user_role and user_role.upper() == self.ADMIN_ROLE:
            return True
        perm: TablePermission = await self.permission_repo.get_permissions(
            table_id=table.id, user_id=user_id
        )
        if perm and perm.can_manage:
            return True
        return False

    async def get_permissions(
        self, table_id: int, user_id: int, user_role: str
    ) -> list[TablePermissionResponse]:
        """Получить список всех прав доступа для указанной таблицы."""
        await self._check_table_access(
            table_id=table_id, user_id=user_id, user_role=user_role
        )

        perms = await self.permission_repo.get_permissions_by_table(table_id=table_id)
        return [self._to_response(p) for p in perms]

    async def create_permission(
        self,
        table_id: int,
        user_id: int,
        user_role: str,
        data: TablePermissionCreate,
    ) -> TablePermissionResponse:
        """Создать новое право доступа для пользователя на указанную таблицу."""
        await self._check_table_access(table_id, user_id, user_role)

        if await self.permission_repo.get_permissions(
            table_id=table_id, user_id=user_id
        ):
            raise PermissionAlreadyExistsException()

        if not (
            perm := await self.permission_repo.create_permission(
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
        self, table_id: int, target_user_id: int, user_id: int, user_role: str
    ) -> None:
        await self._check_table_access(table_id, user_id, user_role)

        if not (
            await self.permission_repo.delete_permission(
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
