from fastapi import status


class AppException(Exception):
    """Базовое доменное исключение"""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, message: str = None):
        self.message = message or self.detail
        super().__init__(self.message)


# Пользователь уже существует
class UserAlreadyExistsException(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь уже существует"


# Пользователь не найден
class UserNotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Пользователь не найден"


# Отсутствует идентификатор пользователя
class UserIdNotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Отсутствует идентификатор пользователя"


# Неверная почта или пароль
class IncorrectEmailOrPasswordException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Неверная почта или пароль"


# Токен истек
class TokenExpiredException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Токен истек"


# Некорректный формат токена
class InvalidTokenFormatException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Некорректный формат токена"


# Токен отсутствует в заголовке
class TokenNotFoundException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Токен отсутствует в заголовке"


# Невалидный JWT токен
class NoJwtException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Токен не валидный"


# Не найден ID пользователя
class NoUserIdException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Не найден ID пользователя"


# Недостаточно прав
class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Недостаточно прав"


class TokenInvalidFormatException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Неверный формат токена. Ожидается 'Bearer <токен>'"


# Нет доступа к данной таблице
class AccessDeniedException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Нет доступа к данной таблице"


# Не найдено
class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Not Found"


# Невалидный refresh token
class InvalidRefreshTokenException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid refresh token"


# Пользователь неактивен или не найден
class UserInactiveException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "User not found or inactive"
