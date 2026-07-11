from fastapi import Header, Depends

from typing import AsyncGenerator, Annotated

from chat_service.app.core import UnitOfWork, AsyncSessionFactory
from chat_service.app.services import ChatService


async def get_current_user_email(
    x_user_email: str = Header(..., alias="X-User-Email"),
) -> str:
    """Получить email текущего пользователя из заголовка"""
    return x_user_email


async def get_async_uow_session() -> AsyncGenerator[UnitOfWork, None]:
    uow = UnitOfWork(AsyncSessionFactory)
    async with uow.start():
        yield uow


def get_chat_service(
    uow: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> ChatService:
    """Получить экземпляр сервиса разрешений пользователей."""
    return ChatService(uow)
