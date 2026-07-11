from fastapi import APIRouter, Depends, status, Query

from typing import Annotated

from chat_service.app.schemas import DialogOut, MessageOut, MessageCreateRequest
from chat_service.app.api.dependencies import get_current_user_email, get_chat_service
from chat_service.app.schemas.chat import PaginatedResponse
from chat_service.app.services import ChatService


router = APIRouter()


@router.get(
    "/users", response_model=list[DialogOut], summary="Получить список диалогов"
)
async def get_dialogs(
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    user_email: str = Depends(get_current_user_email),
) -> list[DialogOut]:
    """Возвращает все диалоги текущего пользователя с последним сообщением и счетчиком непрочитанных."""
    return await chat_service.get_dialogs(user_email)


@router.post(
    "/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Получатель не найден"},
        400: {"description": "Нельзя написать самому себе"},
        403: {"description": "Получатель заблокирован"},
    },
)
async def send_message(
    data: MessageCreateRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    user_email: str = Depends(get_current_user_email),
) -> MessageOut:
    """
    Создает новое сообщение.
    Автоматически создает чат, если его еще нет.
    Commit выполняется автоматически через UnitOfWork.
    """
    return await chat_service.send_message(user_email, data)


@router.get(
    "/messages/{interlocutor_email}",
    response_model=PaginatedResponse,
    summary="Получить историю сообщений с конкретным пользователем",
)
async def get_messages(
    interlocutor_email: str,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    user_email: str = Depends(get_current_user_email),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaginatedResponse:
    """Возвращает пагинированную историю переписки с указанным собеседником (новые сверху)."""
    return await chat_service.get_messages(
        user_email, interlocutor_email, limit, offset
    )
