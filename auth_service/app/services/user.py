from auth_service.app.events import event_publisher
from auth_service.app.exceptions import ForbiddenException
from auth_service.app.schemas import SUserInfo, UserRole
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
        return [
            SUserInfo.model_validate(t) for t in (await uow_session.user.find_all())
        ]

    async def get_user_by_id(
        self, uow_session: UnitOfWork, user_id: int
    ) -> SUserInfo | None:
        async with uow_session.start():
            user = uow_session.user.find_one_or_none_by_id(user_id=user_id)
            if not user:
                return None

            return SUserInfo.model_validate(user)

    async def get_user_by_email(
        self, uow_session: UnitOfWork, email: str
    ) -> SUserInfo | None:
        user = await uow_session.user.find_by_email(email=email)
        if not user:
            return None
        return SUserInfo.model_validate(user)

    async def delete_user(self, uow_session: UnitOfWork, user_id: int) -> bool:
        return await uow_session.user.delete_by_id(user_id=user_id)

    async def deactivate_user(
        self, uow_session: UnitOfWork, user_id: int
    ) -> SUserInfo | None:
        result = await uow_session.user.deactivate_user(user_id=user_id)
        if not result:
            return None
        user = await uow_session.user.find_one_or_none_by_id(user_id=user_id)
        if not user:
            return None
        return SUserInfo.model_validate(user)
