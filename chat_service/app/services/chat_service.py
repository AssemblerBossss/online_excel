from sqlalchemy.ext.asyncio import AsyncSession
import datetime

from chat_service.app.repository import ChatRepository
from chat_service.app.models import Message
from chat_service.app.schemas import MessageCreateRequest, DialogOut
from chat_service.app.exceptions import (
    SelfMessageException,
    UserNotFoundException,
    UserBlockedException,
)


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ChatRepository(session)

    async def send_message(
        self, sender_email: str, data: MessageCreateRequest
    ) -> Message:
        if sender_email == data.receiver_email:
            raise SelfMessageException("Нельзя отправить сообщение самому себе")

        receiver = await self.repo.get_user_by_email(data.receiver_email)
        if not receiver:
            raise UserNotFoundException(f"Пользователь {data.receiver_email} не найден")
        if not receiver.is_active:
            raise UserBlockedException(
                f"Пользователь {data.receiver_email} заблокирован"
            )

        user1, user2 = sorted([sender_email, data.receiver_email])
        chat = await self.repo.get_chat_by_users(user1, user2)
        if not chat:
            chat = await self.repo.create_chat(user1, user2)

        message = await self.repo.add_message(
            chat=chat.id,
            sender_email=sender_email,
            receiver_email=receiver.email,
            content=data.content,
        )
        chat.last_message_content = data.content
        chat.last_message_at = message.created_at or datetime.datetime.now(datetime.UTC)

        if receiver.email == chat.user1_email:
            chat.unread_count_user1 += 1
        else:
            chat.unread_count_user2 += 1

        return message

    async def get_dialogs(self, current_user_email: str) -> list[DialogOut]:
        """
        Логика получения списка диалогов
        """

        chats = await self.repo.get_dialogs_for_user(user_email=current_user_email)
        result = []

        for chat in chats:
            if current_user_email == chat.user1_email:
                interlocutor = chat.user2_email
                unread = chat.unread_count_user1
            else:
                interlocutor = chat.user1_email
                unread = chat.unread_count_user2

            result.append(DialogOut(
                interlocutor_email=interlocutor,
                last_message_content=chat.last_message_content,
                last_message_at=chat.last_message_at,
                unread_count=unread,
            ))

        return result
