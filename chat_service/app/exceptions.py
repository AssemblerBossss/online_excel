from fastapi import status, HTTPException


class ChatException(HTTPException):
    """Базовое исключение для чата"""

    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class SelfMessageException(ChatException):
    """Нельзя отправить сообщение самому себе"""

    def __init__(self, detail: str = "Нельзя отправить сообщение самому себе"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UserNotFoundException(ChatException):
    """Пользователь не найден"""

    def __init__(self, email: str = None):
        detail = (
            f"Пользователь {email} не найден" if email else "Пользователь не найден"
        )
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UserBlockedException(ChatException):
    """Пользователь заблокирован"""

    def __init__(self, email: str = None):
        detail = (
            f"Пользователь {email} заблокирован"
            if email
            else "Пользователь заблокирован"
        )
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
