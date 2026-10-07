import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.exc import IntegrityError

from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.exceptions import (
    AccessDeniedException,
    CanNotCreatePermissionException,
    NotFoundException,
    PermissionAlreadyExistsException,
    UserNotFoundException,
)
from table_service.app.models import DataTable, TablePermission
from table_service.app.schemas import (
    TablePermissionCreate,
    TablePermissionResponse,
    TablePermissionUpdate,
)

logger = logging.getLogger(__name__)


class PermissionService:
    ADMIN_ROLE = "ADMIN"

    @staticmethod
    def _to_response(
        permission: TablePermission, email: str | None = None
    ) -> TablePermissionResponse:
        return TablePermissionResponse(
            id=permission.id,
            user_id=permission.user_id,
            table_id=permission.table_id,
            user_email=email,
            can_read=permission.can_read,
            can_write=permission.can_write,
            can_manage=permission.can_manage,
            created_at=permission.created_at,
        )

    async def _get_table_with_access(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        check_access_func: Callable[..., Awaitable[bool]],
        access_type: str,
        is_deleted: bool = False,
    ) -> DataTable:
        """Внутренний метод для получения таблицы и проверки прав доступа."""
        # 1. Получение таблицы в зависимости от флага is_deleted
        if is_deleted:
            table = await uow_session.tables.get_deleted_table_by_id(table_id=table_id)
            not_found_msg = "Таблица не найдена в корзине"
        else:
            table = await uow_session.tables.get_table_by_id(table_id=table_id)
            not_found_msg = "Таблица не найдена"

        if not table:
            raise NotFoundException(not_found_msg)

        # 2. Проверка доступа переданной функцией
        has_access = await check_access_func(
            uow_session=uow_session, table=table, user_id=user_id, user_role=user_role
        )

        # 3. Логирование и вызов ошибки, если доступа нет
        if not has_access:
            logger.warning(
                "User %s denied %s access to table %s", user_id, access_type, table_id
            )
            raise AccessDeniedException()

        return table

    async def get_table_with_read_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        """Найти таблицу по ID и проверить право на чтение."""
        return await self._get_table_with_access(
            uow_session=uow_session,
            table_id=table_id,
            user_id=user_id,
            user_role=user_role,
            check_access_func=self.check_read_access,
            access_type="read",
        )

    async def get_table_with_write_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        """Получить таблицу по ID и проверить доступ на запись."""
        return await self._get_table_with_access(
            uow_session=uow_session,
            table_id=table_id,
            user_id=user_id,
            user_role=user_role,
            check_access_func=self.check_write_access,
            access_type="write",
        )

    async def get_table_with_manage_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        """Получить таблицу по ID и проверить доступ на управление."""
        return await self._get_table_with_access(
            uow_session=uow_session,
            table_id=table_id,
            user_id=user_id,
            user_role=user_role,
            check_access_func=self.check_manage_access,
            access_type="manage",
        )

    async def get_deleted_table_with_manage_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        """Получить удаленную таблицу по ID и проверить доступ на управление."""
        return await self._get_table_with_access(
            uow_session=uow_session,
            table_id=table_id,
            user_id=user_id,
            user_role=user_role,
            check_access_func=self.check_manage_access,
            access_type="manage",
            is_deleted=True,
        )

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
        return bool(perm and (perm.can_read or perm.can_write or perm.can_manage))

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
        return bool(perm and (perm.can_write or perm.can_manage))

    async def check_manage_access(
        self, uow_session: UnitOfWork, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверить, имеет ли пользователь право на управление (изменение прав, удаление таблицы)."""
        if table.created_by_id == user_id:
            return True
        if user_role and user_role.upper() == self.ADMIN_ROLE:
            return True
        perm: TablePermission | None = await uow_session.permissions.get_permissions(
            table_id=table.id, user_id=user_id
        )
        return bool(perm and perm.can_manage)

    async def get_permissions(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> list[TablePermissionResponse]:
        """Получить список всех прав доступа для указанной таблицы."""
        async with uow_session.start():
            await self.get_table_with_manage_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            perms = await uow_session.permissions.get_permissions_by_table(
                table_id=table_id
            )
            return [self._to_response(p, email=email) for p, email in perms]

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
            await self.get_table_with_manage_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )

            target_user = await uow_session.users.get_by_email(data.email)
            if not target_user:
                raise UserNotFoundException()

            if target_user.id == user_id:
                raise PermissionAlreadyExistsException()

            if await uow_session.permissions.get_permissions(
                table_id=table_id, user_id=target_user.id
            ):
                raise PermissionAlreadyExistsException()

            try:
                perm = await uow_session.permissions.create_permission(
                    table_id=table_id,
                    user_id=target_user.id,
                    can_read=data.can_read,
                    can_write=data.can_write,
                    can_manage=data.can_manage,
                )
            except IntegrityError:
                # Если два запроса пришли одновременно, второй упадет здесь,
                # и мы вернем  409 ошибку.
                raise PermissionAlreadyExistsException()

            if not perm:
                raise CanNotCreatePermissionException()

            logger.info(
                "User %s granted permission %s to user %s (%s) on table %s",
                user_id,
                perm.id,
                target_user.id,
                target_user.email,
                table_id,
            )
            return self._to_response(perm, email=target_user.email)

    async def update_permission(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        target_user_id: int,
        user_role: str,
        data: TablePermissionUpdate,
    ) -> TablePermissionResponse:
        """Изменить существующие права пользователя на таблицу."""
        async with uow_session.start():
            await self.get_table_with_manage_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )
            payload = data.model_dump(exclude_none=True)
            if not payload:
                existing = await uow_session.permissions.get_permissions(
                    table_id=table_id, user_id=target_user_id
                )
                if not existing:
                    raise NotFoundException("Права для данного пользователя не найдены")
                return self._to_response(existing)

            updated_permission = await uow_session.permissions.update_permission(
                table_id=table_id, user_id=target_user_id, **payload
            )

            if not updated_permission:
                raise NotFoundException("Права для данного пользователя не найдены")

            logger.info(
                "User %s updated permission for user %s on table %s: %s",
                user_id,
                target_user_id,
                table_id,
                payload,
            )
            return self._to_response(updated_permission)

    async def delete_permission(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        target_user_id: int,
        user_id: int,
        user_role: str,
    ) -> None:
        """Отозвать все права пользователя на таблицу."""
        async with uow_session.start():
            await self.get_table_with_manage_access(
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
