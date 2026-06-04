from datetime import datetime, timezone

from auth_service.app.config import auth_service_settings
from auth_service.app.events import event_publisher
from auth_service.app.exceptions import (
    ForbiddenException,
    FileTooLargeException,
    UserAlreadyExistsException,
    UserNotFoundException,
    IncorrectPasswordException,
)
from auth_service.app.schemas import (
    SUserInfo,
    UserRole,
    SUserProfileUpdate,
    UserUpdateEvent,
    SUserChangePassword,
)
from auth_service.app.utils import avatar_storage, get_password_hash, verify_password
from auth_service.app.сore import UnitOfWork


class UserService:
    def __init__(self):
        self.event_publisher = event_publisher

    @staticmethod
    async def _check_permissions(current_user: SUserInfo, target_user_id: int) -> None:
        if current_user.role != UserRole.ADMIN and current_user.id != target_user_id:
            raise ForbiddenException()

    @staticmethod
    async def _check_is_admin(current_user: SUserInfo) -> None:
        if current_user.role != UserRole.ADMIN:
            raise ForbiddenException()

    async def get_all_users(self, uow_session: UnitOfWork) -> list[SUserInfo]:
        """Возвращает список всех пользователей"""
        return [
            SUserInfo.model_validate(t) for t in (await uow_session.user.find_all())
        ]

    async def get_user_by_id(
        self, uow_session: UnitOfWork, user_id: int
    ) -> SUserInfo | None:
        """Возвращает пользователя по ID или None, если не найден"""
        async with uow_session.start():
            user = uow_session.user.find_one_or_none_by_id(user_id)
            if not user:
                return None

            return SUserInfo.model_validate(user)

    async def get_user_by_email(
        self, uow_session: UnitOfWork, email: str
    ) -> SUserInfo | None:
        """Возвращает пользователя по email или None, если не найден"""
        async with uow_session.start():
            user = await uow_session.user.find_by_email(email)
            if not user:
                return None
        return SUserInfo.model_validate(user)

    async def change_role(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        user_id: int,
        role: UserRole,
    ) -> SUserInfo | None:
        """Сменить роль пользователя. Доступно только админу."""
        if current_user.role != UserRole.ADMIN:
            raise ForbiddenException()
        async with uow_session.start():
            updated = await uow_session.user.change_user_role(
                user_id=user_id, new_role=role
            )
            if not updated:
                return None
            user = await uow_session.user.find_one_or_none_by_id(user_id)
        await self.event_publisher.publish(
            UserUpdateEvent(
                user_id=user_id,
                email=user.email,
                role=str(user.role),
                timestamp=datetime.now(timezone.utc),
            )
        )
        return SUserInfo.model_validate(user)

    async def update_avatar(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        user_id: int,
        content: bytes,
        content_type: str | None,
    ) -> SUserInfo | None:
        """Загрузить/заменить аватар. Админ - любому, пользователь - только себе."""
        await self._check_permissions(current_user=current_user, target_user_id=user_id)

        if len(content) > auth_service_settings.MAX_AVATAR_SIZE:
            raise FileTooLargeException()

        object_name: str = await avatar_storage.upload_avatar(
            content=content, content_type=content_type
        )

        async with uow_session.start():
            updated = await uow_session.user.set_avatar(
                user_id=user_id, object_name=object_name
            )
            if not updated:
                await avatar_storage.delete(object_name)
                return None
            user = await uow_session.user.find_one_or_none_by_id(user_id)
            return SUserInfo.model_validate(user)

    async def update_user(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        user_id: int,
        data: SUserProfileUpdate,
    ) -> SUserInfo | None:
        """Обновить профиль. Админ - любого, пользователь - только себя."""
        await self._check_permissions(current_user, user_id)

        values = data.model_dump(exclude_unset=True)
        async with uow_session.start():
            if "email" in values:
                existing = await uow_session.user.find_by_email(email=values["email"])
                if existing and existing.id != user_id:
                    raise UserAlreadyExistsException
            if values:
                await uow_session.user.update_by_id(user_id, values=values)
            user = await uow_session.user.find_one_or_none_by_id(user_id=user_id)
            if not user:
                return None

        # Проекция в table_service хранит только email/role — событие нужно лишь при смене email
        if "email" in values:
            await self.event_publisher.publish(
                UserUpdateEvent(
                    user_id=str(user.id),
                    email=user.email,
                    role=str(user.role),
                    timestamp=datetime.now(timezone.utc),
                )
            )
        return SUserInfo.model_validate(user)

    async def delete_avatar(
        self, uow_session: UnitOfWork, current_user: SUserInfo, user_id: int
    ) -> SUserInfo | None:
        """Удалить аватар. Админ - любому, пользователь - только себе."""
        await self._check_permissions(current_user=current_user, target_user_id=user_id)

        async with uow_session.start():
            user = await uow_session.user.find_one_or_none_by_id(user_id)
            if not user:
                return None
            object_name: str = user.avatar_url

            await uow_session.user.clear_avatar(user_id)
            user = await uow_session.user.find_one_or_none_by_id(user_id)

        await avatar_storage.delete(object_name)
        return SUserInfo.model_validate(user)

    async def delete_user(
        self, uow_session: UnitOfWork, current_user: SUserInfo, user_id: int
    ) -> bool:
        """Удалить пользователя. Админ - любого, обычный пользователь - только себя."""
        await self._check_permissions(current_user, user_id)
        return await uow_session.user.delete_by_id(user_id)

    async def deactivate_user(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        user_id: int,
    ) -> SUserInfo | None:
        """Деактивировать пользователя. Админ - любого, пользователь - только себя."""
        await self._check_permissions(current_user, user_id)

        async with uow_session.start():
            result = await uow_session.user.change_user_active_status(user_id, False)
            if not result:
                return None
            user = await uow_session.user.find_one_or_none_by_id(user_id)
            if not user:
                return None

        return SUserInfo.model_validate(user)

    async def activate_user(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        user_id: int,
    ) -> SUserInfo | None:
        """Активировать пользователя. Может только админ"""
        await self._check_is_admin(current_user)

        async with uow_session.start():
            result = await uow_session.user.change_user_active_status(user_id, True)
            if not result:
                return None
            user = await uow_session.user.find_one_or_none_by_id(user_id)
            if not user:
                return None

        return SUserInfo.model_validate(user)

    async def change_password(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        data: SUserChangePassword,
    ) -> None:
        """Сменить пароль текущего пользователя"""
        async with uow_session.start():
            user = await uow_session.user.find_one_or_none_by_id(current_user.id)
            if not user:
                raise UserNotFoundException()
            if not verify_password(data.old_password, user.hashed_password):
                raise IncorrectPasswordException()

            await uow_session.user.update_by_id(
                current_user.id,
                values={"hashed_password": get_password_hash(data.new_password)},
            )
