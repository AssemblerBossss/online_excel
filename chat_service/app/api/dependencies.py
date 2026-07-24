from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header

from chat_service.app.core import AsyncSessionFactory, UnitOfWork
from chat_service.app.services import ChatService


async def get_current_user_email(
    x_user_email: str = Header(..., alias="X-User-Email"),
) -> str:
    """Получить email текущего пользователя из заголовка"""
    return x_user_email


async def get_async_uow_session() -> AsyncGenerator[UnitOfWork]:
    uow = UnitOfWork(AsyncSessionFactory)
    async with uow.start():
        yield uow


def get_chat_service(
    uow: Annotated[UnitOfWork, Depends(get_async_uow_session)],
) -> ChatService:
    """Получить экземпляр сервиса разрешений пользователей."""
    return ChatService(uow)
