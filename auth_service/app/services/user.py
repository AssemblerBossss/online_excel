import logging
from datetime import UTC, datetime

from auth_service.app.config import auth_service_settings
from auth_service.app.events import event_publisher
from auth_service.app.exceptions import (
    FileTooLargeException,
    ForbiddenException,
    IncorrectPasswordException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from auth_service.app.schemas import (
    SUserChangePassword,
    SUserInfo,
    SUserProfileUpdate,
    UserDeletedEvent,
    UserRole,
    UserUpdateEvent,
)
from auth_service.app.utils import avatar_storage, get_password_hash, verify_password
from auth_service.app.сore import UnitOfWork

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self):
        self.event_publisher = event_publisher

    @staticmethod
    def _check_permissions(current_user: SUserInfo, target_user_id: int) -> None:
        if current_user.role != UserRole.ADMIN and current_user.id != target_user_id:
            raise ForbiddenException()

    @staticmethod
    def _check_is_admin(current_user: SUserInfo) -> None:
        if current_user.role != UserRole.ADMIN:
            raise ForbiddenException()

    async def get_all_users(self, uow_session: UnitOfWork) -> list[SUserInfo]:
        """Возвращает список всех пользователей"""
        async with uow_session.start():
            return [
                SUserInfo.model_validate(t) for t in (await uow_session.user.find_all())
            ]

    async def get_user_by_id(
        self, uow_session: UnitOfWork, user_id: int
    ) -> SUserInfo | None:
        """Возвращает пользователя по ID или None, если не найден"""
        async with uow_session.start():
            user = await uow_session.user.find_one_or_none_by_id(user_id)
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
                role=str(user.role.value),
                timestamp=datetime.now(UTC),
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
        self._check_permissions(current_user=current_user, target_user_id=user_id)

        if len(content) > auth_service_settings.MAX_AVATAR_SIZE:
            raise FileTooLargeException()

        object_name = await avatar_storage.upload_avatar(
            content, content_type=content_type
        )

        try:
            async with uow_session.start():
                user = await uow_session.user.find_one_or_none_by_id(user_id)
                if not user:
                    await avatar_storage.delete(object_name)
                    return None
                old_object_name = user.avatar_url
                await uow_session.user.set_avatar(
                    user_id=user_id, object_name=object_name
                )
                user.avatar_url = object_name
            if old_object_name:
                try:
                    await avatar_storage.delete(old_object_name)
                except Exception as e:
                    # Если старый аватар не удалился, мы НЕ должны падать с ошибкой.
                    # Просто логируем. "Мусор" в хранилище потом уберет крон.
                    logger.warning(
                        f"Failed to delete old avatar {old_object_name}: {e}"
                    )
            return SUserInfo.model_validate(user)

        except Exception:
            await avatar_storage.delete(object_name)
            raise


    async def update_user(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        user_id: int,
        data: SUserProfileUpdate,
    ) -> SUserInfo | None:
        """Обновить профиль. Админ - любого, пользователь - только себя."""
        self._check_permissions(current_user, user_id)

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
                    user_id=user.id,
                    email=user.email,
                    role=str(user.role.value),
                    timestamp=datetime.now(UTC),
                )
            )
        return SUserInfo.model_validate(user)

    async def delete_avatar(
        self, uow_session: UnitOfWork, current_user: SUserInfo, user_id: int
    ) -> SUserInfo | None:
        """Удалить аватар. Админ - любому, пользователь - только себе."""
        self._check_permissions(current_user=current_user, target_user_id=user_id)

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
        self._check_permissions(current_user, user_id)
        async with uow_session.start():
            user = await uow_session.user.find_one_or_none_by_id(user_id)
            if not user:
                return False
            avatar = user.avatar_url
            await uow_session.user.delete_by_id(user_id)

        await self.event_publisher.publish(
            UserDeletedEvent(user_id=user_id, timestamp=datetime.now(UTC))
        )
        try:
            await avatar_storage.delete(avatar)
        except Exception:
            logger.exception("Не удалось удалить аватар %s", avatar)

        return True

    async def deactivate_user(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        user_id: int,
    ) -> SUserInfo | None:
        """Деактивировать пользователя. Админ - любого, пользователь - только себя."""
        self._check_permissions(current_user, user_id)

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
        self._check_is_admin(current_user)

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
            # Отозвать сессию после смены пароля
            await uow_session.token.revoke_all_user_tokens(user_id=current_user.id)
