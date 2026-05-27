from auth_service.app.config import auth_service_settings
from auth_service.app.events import event_publisher
from auth_service.app.exceptions import ForbiddenException, FileTooLargeException
from auth_service.app.schemas import SUserInfo, UserRole
from auth_service.app.utils import avatar_storage
from auth_service.app.сore import UnitOfWork


class UserService:
    def __init__(self):
        self.event_publisher = event_publisher

    async def _check_permissions(
        self, current_user: SUserInfo, target_user_id: int
    ) -> None:
        if current_user.role != UserRole.ADMIN and current_user.id != target_user_id:
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
            user = uow_session.user.find_one_or_none_by_id(user_id=user_id)
            if not user:
                return None

            return SUserInfo.model_validate(user)

    async def get_user_by_email(
        self, uow_session: UnitOfWork, email: str
    ) -> SUserInfo | None:
        """Возвращает пользователя по email или None, если не найден"""
        user = await uow_session.user.find_by_email(email=email)
        if not user:
            return None
        return SUserInfo.model_validate(user)

    async def delete_user(
        self, uow_session: UnitOfWork, current_user: SUserInfo, user_id: int
    ) -> bool:
        """Удалить пользователя. Админ — любого, обычный пользователь — только себя."""
        await self._check_permissions(current_user, user_id)
        return await uow_session.user.delete_by_id(user_id=user_id)

    async def deactivate_user(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        user_id: int,
    ) -> SUserInfo | None:
        """Деактивировать пользователя. Админ — любого, пользователь — только себя."""
        await self._check_permissions(current_user, user_id)
        result = await uow_session.user.deactivate_user(user_id=user_id)
        if not result:
            return None
        user = await uow_session.user.find_one_or_none_by_id(user_id=user_id)
        if not user:
            return None
        return SUserInfo.model_validate(user)

    async def update_avatar(
        self,
        uow_session: UnitOfWork,
        current_user: SUserInfo,
        user_id: int,
        content: bytes,
        content_type: str | None,
    ):
        """Загрузить/заменить аватар. Админ — любому, пользователь — только себе."""
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
            user = await uow_session.user.find_one_or_none_by_id(user_id=user_id)
            return SUserInfo.model_validate(user)
