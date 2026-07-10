from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from chat_service.app.models import Chat, Message
import uuid


class ChatRepository:
    def __init_(self, session: AsyncSession):
        self._session = session

    async def get_dialogs_for_user(self, user_email: str) -> list[Chat]:
        """
        Достаем все чаты, где участвует пользователь, отсортированные по последнему сообщению.
        """
        stmt = (
            select(Chat)
            .where(or_(Chat.user1_email == user_email, Chat.user2_email == user_email))
            .order_by(Chat.last_message_at.desc().nullslast())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_chat_by_users(
        self, user1_email: str, user2_email: str
    ) -> Chat | None:
        """
        Ищет конкретный чат. На вход подаются уже отсортированные email'ы
        """
        stmt = select(Chat).where(
            and_(user1_email == Chat.user1_email, user2_email == Chat.user2_email)
        )
        result = await self._session.execute(stmt)
        return result.scalars.first()

    async def create_chat(self, user1_email: str, user2_email: str) -> Chat:
        """Создает новую запись в таблице Chats"""
        new_chat = Chat(user1_email=user1_email, user2_email=user2_email)
        self._session.add(new_chat)
        await self._session.flush()
        return new_chat

    async def add_message(
        self, chat_id: uuid.UUID, sender_email: str, receiver_email: str, content: str
    ) -> Message:
        new_msg = Message(
            chat_id=chat_id,
            sender_email=sender_email,
            receiver_email=receiver_email,
            content=content,
        )
        self._session.add(new_msg)
        await self._session.flush()
        return new_msg

    async def get_messages(
        self, chat_id: uuid.UUID, limit: int = 30, offset: int = 0
    ) -> list[Message]:
        """Получить историю конкретного чата с пагинацией"""
        stmt = (
            select(Message)
            .where(chat_id == Message.chat_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
