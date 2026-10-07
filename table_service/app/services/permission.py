import logging
from typing import Awaitable, Callable
from redis.asyncio import Redis
from collections.abc import Awaitable, Callable
from sqlalchemy.exc import IntegrityError

from table_service.app.services.cache import AccessCache, AccessLevel
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
ACCESS_CACHE_TTL = 60


class PermissionService:
    ADMIN_ROLE = "ADMIN"

    def __init__(self, redis: Redis):
        self.redis = redis
        self.cache = AccessCache(redis, ttl=ACCESS_CACHE_TTL)

    # ------------------------------------------------------------------ utils

    @staticmethod
    def _to_response(
        permission: TablePermission, email: str | None = None
    ) -> TablePermissionResponse:
        """Собирает ответ API из модели TablePermission, опционально подставляя email пользователя"""
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

    def _is_admin(self, user_role: str | None) -> bool:
        """Проверяет, что роль пользователя — ADMIN (без учёта регистра)."""
        return bool(user_role and user_role.upper() == self.ADMIN_ROLE)

    async def invalidate_table_access(self, table_id: int) -> None:
        """Сбросить кэш доступа всех пользователей к таблице.

        Вызывать после коммита при любом изменении, влияющем на доступ:
        права, is_public, удаление/восстановление таблицы, смена владельца.
        """
        await self.cache.bump_table(table_id)

    # ------------------------------------------------- uncached check methods
    # Чистая логика "есть ли доступ". Кэш сюда НЕ встраивается.

    async def check_read_access(
        self, uow_session: UnitOfWork, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверяет право на чтение таблицы без кеша"""
        if table.created_by_id == user_id or self._is_admin(user_role):
            return True
        if table.is_public:
            return True
        perm = await uow_session.permissions.get_permissions(
            table_id=table.id, user_id=user_id
        )
        return bool(perm and (perm.can_read or perm.can_write or perm.can_manage))

    async def check_write_access(
        self, uow_session: UnitOfWork, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверяет право на запись без кеша: владелец, админ или разрешение can_write/can_manage"""
        if table.created_by_id == user_id or self._is_admin(user_role):
            return True
        perm = await uow_session.permissions.get_permissions(
            table_id=table.id, user_id=user_id
        )
        return bool(perm and (perm.can_write or perm.can_manage))

    async def check_manage_access(
        self, uow_session: UnitOfWork, table: DataTable, user_id: int, user_role: str
    ) -> bool:
        """Проверяет право на управление без кеша: владелец, админ или разрешение can_manage"""
        if table.created_by_id == user_id or self._is_admin(user_role):
            return True
        perm = await uow_session.permissions.get_permissions(
            table_id=table.id, user_id=user_id
        )
        return bool(perm and perm.can_manage)

    def _checker(self, level: AccessLevel) -> Callable[..., Awaitable[bool]]:
        """Возвращает функцию проверки доступа, соответствующую уровню AccessLevel"""
        return {
            AccessLevel.READ: self.check_read_access,
            AccessLevel.WRITE: self.check_write_access,
            AccessLevel.MANAGE: self.check_manage_access,
        }[level]

    # -----single entry point (cached)------ #

    async def ensure_access(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        level: AccessLevel,
    ) -> None:
        """Единая точка проверки доступа с кэшем. Бросает исключение, если доступа нет.

        Ничего не возвращает: если нужна сама таблица, используйте
        get_table_with_*_access (они всегда ходят в БД, т.к. таблица нужна всё равно).
        Не вызывать внутри уже открытого `async with uow_session.start()`.
        """
        if self._is_admin(user_role):
            return

        version, cached = await self.cache.lookup(table_id, user_id, level)
        if cached:
            return
        if cached is False:
            logger.warning(
                "User %s denied %s access to table %s (cached)",
                user_id,
                level.value,
                table_id,
            )
            raise AccessDeniedException()

        async with uow_session.start():
            table = await uow_session.tables.get_table_by_id(table_id=table_id)
            if not table:
                raise NotFoundException("Таблица не найдена")
            has_access = await self._checker(level)(
                uow_session=uow_session,
                table=table,
                user_id=user_id,
                user_role=user_role,
            )

        await self.cache.store(
            table_id=table_id,
            user_id=user_id,
            level=level,
            version=version,
            value=has_access,
        )

        if not has_access:
            logger.warning(
                "User %s denied %s access to table %s", user_id, level.value, table_id
            )
            raise AccessDeniedException()

    async def _get_table_with_access(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        level: AccessLevel,
        is_deleted: bool = False,
    ) -> DataTable:
        """Загружает таблицу и проверяет доступ. Всегда идёт в БД."""
        if is_deleted:
            table = await uow_session.tables.get_deleted_table_by_id(table_id=table_id)
            not_found_msg = "Таблица не найдена в корзине"
        else:
            table = await uow_session.tables.get_table_by_id(table_id=table_id)
            not_found_msg = "Таблица не найдена"

        if not table:
            raise NotFoundException(not_found_msg)

        has_access = await self._checker(level)(
            uow_session=uow_session, table=table, user_id=user_id, user_role=user_role
        )
        if not has_access:
            logger.warning(
                "User %s denied %s access to table %s",
                user_id,
                level.value,
                table_id,
            )
            raise AccessDeniedException()
        return table

    async def get_table_with_read_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        """Возвращает таблицу, если у пользователя есть право на чтение."""
        return await self._get_table_with_access(
            uow_session, table_id, user_id, user_role, AccessLevel.READ
        )

    async def get_table_with_write_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        """Возвращает таблицу, если у пользователя есть право на запись."""
        return await self._get_table_with_access(
            uow_session, table_id, user_id, user_role, AccessLevel.WRITE
        )

    async def get_table_with_manage_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        """Возвращает таблицу, если у пользователя есть право на управление."""
        return await self._get_table_with_access(
            uow_session, table_id, user_id, user_role, AccessLevel.MANAGE
        )

    async def get_deleted_table_with_manage_access(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> DataTable:
        """Возвращает удалённую таблицу (из корзины), если у пользователя есть право на управление."""
        return await self._get_table_with_access(
            uow_session,
            table_id,
            user_id,
            user_role,
            AccessLevel.MANAGE,
            is_deleted=True,
        )

    # Инвалидация делается ПОСЛЕ выхода из `async with uow_session.start()`,
    # то есть после коммита. Если сбросить кэш до коммита, параллельный запрос
    # может перекэшировать старое состояние уже под новой версией.

    async def get_permissions(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> list[TablePermissionResponse]:
        """Возвращает список разрешений на таблицу; требует права на управление"""
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
        """
        Выдаёт разрешение пользователю по email; проверяет право на управление,
        существование пользователя и отсутствие дубликата, сбрасывает кеш доступов
        """
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

            response = self._to_response(perm, email=target_user.email)
            target_id, target_email, perm_id = (
                target_user.id,
                target_user.email,
                perm.id,
            )

        await self.invalidate_table_access(table_id)
        logger.info(
            "User %s granted permission %s to user %s (%s) on table %s",
            user_id,
            perm_id,
            target_id,
            target_email,
            table_id,
        )
        return response

    async def update_permission(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        target_user_id: int,
        user_role: str,
        data: TablePermissionUpdate,
    ) -> TablePermissionResponse:
        """
        Обновляет разрешение пользователя на таблицу; пустой payload возвращает текущее
        разрешение, при отсутствии записи — NotFoundException, сбрасывает кеш.
        """
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

            updated = await uow_session.permissions.update_permission(
                table_id=table_id, user_id=target_user_id, **payload
            )
            if not updated:
                raise NotFoundException("Права для данного пользователя не найдены")
            response = self._to_response(updated)

        await self.invalidate_table_access(table_id)
        logger.info(
            "User %s updated permission for user %s on table %s: %s",
            user_id,
            target_user_id,
            table_id,
            payload,
        )
        return response

    async def delete_permission(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        target_user_id: int,
        user_id: int,
        user_role: str,
    ) -> None:
        """Отзывает разрешение пользователя на таблицу; требует право на управление, сбрасывает кеш."""
        async with uow_session.start():
            await self.get_table_with_manage_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )
            deleted = await uow_session.permissions.delete_permission(
                table_id=table_id, user_id=target_user_id
            )
            if not deleted:
                raise NotFoundException("Права для данного пользователя не найдены")

        await self.invalidate_table_access(table_id)
        logger.info(
            "User %s revoked permissions on table %s from user %s",
            user_id,
            table_id,
            target_user_id,
        )
