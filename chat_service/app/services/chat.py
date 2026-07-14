from fastapi import BackgroundTasks
import datetime
from chat_service.app.schemas import (
    MessageCreateRequest,
    DialogOut,
    MessageOut,
    PaginatedResponse,
)
from chat_service.app.exceptions import (
    SelfMessageException,
    UserNotFoundException,
    UserBlockedException,
)
from chat_service.app.core import UnitOfWork
from chat_service.app.core.realtime import publish_new_message


class ChatService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow
        self.repo = uow.chat_repo

    async def send_message(
        self,
        sender_email: str,
        data: MessageCreateRequest,
        background_tasks: BackgroundTasks,
    ) -> MessageOut:
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
            chat_id=chat.id,
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

        message_out = MessageOut.model_validate(message)

        background_tasks.add_task(
            publish_new_message,
            target_email=receiver.email,
            chat_id=chat.id,
            message=message_out,
        )

        return message_out

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

            result.append(
                DialogOut(
                    interlocutor_email=interlocutor,
                    last_message_content=chat.last_message_content,
                    last_message_at=chat.last_message_at,
                    unread_count=unread,
                )
            )

        return result

    async def get_messages(
        self,
        current_user_email: str,
        interlocutor_email: str,
        limit: int = 30,
        offset: int = 0,
    ) -> PaginatedResponse:
        """
        Получает историю сообщений между текущим пользователем и собеседником.

        Логика:
        1. Сортируем email'ы для поиска чата (как в send_message)
        2. Ищем чат между пользователями
        3. Если чата нет - возвращаем пустой результат
        4. Получаем сообщения с пагинацией
        5. Конвертируем в Pydantic схемы
        """
        user1, user2 = sorted([interlocutor_email, current_user_email])
        chat = await self.repo.get_chat_by_users(user1_email=user1, user2_email=user2)
        if not chat:
            return PaginatedResponse(
                items=[],
                total=0,
                page=None,
                cursor=None,
            )

        messages = await self.repo.get_messages(
            chat_id=chat.id, limit=limit, offset=offset
        )
        total_messages = await self.repo.count_messages(chat_id=chat.id)
        messages_out = [MessageOut.model_validate(msg) for msg in messages]
        return PaginatedResponse(
            items=messages_out,
            total=total_messages,
            page=None,
            cursor=None,
        )

    async def mark_chat_as_read(
        self, current_user_email: str, interlocutor_email: str
    ) -> int:
        """
        Сбрасывает счетчик непрочитанных для текущего пользователя.
        Возвращает количество помеченных сообщений.
        """
        user1, user2 = sorted([interlocutor_email, current_user_email])
        chat = await self.repo.get_chat_by_users(user1_email=user1, user2_email=user2)
        if not chat:
            return 0

        updated_count = await self.repo.mark_messages_as_read(
            chat_id=chat.id, reader_email=current_user_email
        )
        # Обнуляем денормализованный счетчик у нужного участника
        if updated_count > 0:
            if current_user_email == chat.user1_email:
                chat.unread_count_user1 = 0
            else:
                chat.unread_count_user2 = 0

        return updated_count
