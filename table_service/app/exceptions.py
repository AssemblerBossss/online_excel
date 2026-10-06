class AppException(Exception):
    """Базовое доменное исключение."""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class AccessDeniedException(AppException):
    status_code: int = 403
    detail: str = "Нет доступа к данной таблице"


class ValidationException(AppException):
    status_code: int = 422
    detail: str = "Ошибка валидации данных"


class NotFoundException(AppException):
    status_code: int = 404
    detail: str = "Ресурс не найден"


class CanNotCreateTableException(AppException):
    status_code: int = 400
    detail: str = "Не удалось создать таблицу"


class CanNotDeleteTableException(AppException):
    status_code: int = 409
    detail: str = "Не удалось удалить таблицу"


class ForbiddenException(AppException):
    status_code: int = 403
    detail: str = "Недостаточно прав"


class TokenInvalidFormatException(AppException):
    status_code: int = 401
    detail: str = "Неверный формат токена. Ожидается 'Bearer <токен>'"


class InvalidWSTicketException(AppException):
    status_code: int = 401
    detail: str = "Недействительный или истёкший WebSocket-тикет"


class InvalidFileFormatException(AppException):
    status_code: int = 401
    detail: str = "Неверный формат файла"


class InvalidFileMimeTypeException(AppException):
    status_code: int = 415
    detail: str = "Неподдерживаемый тип файла"


class EmptyFileException(AppException):
    status_code: int = 400
    detail: str = "Файл пустой"


class FileParseException(AppException):
    status_code: int = 400
    detail: str = "Ошибка парсинга файла"


class CanNotUpdateTableException(AppException):
    status_code: int = 400
    detail: str = "Ошибка обновления таблицы"


class PermissionAlreadyExistsException(AppException):
    status_code: int = 409
    detail: str = "Права для этого пользователя уже существуют"


class CanNotCreatePermissionException(AppException):
    status_code: int = 400
    detail: str = "Не удалось создать права доступа"


class UserNotFoundException(AppException):
    status_code: int = 404
    detail: str = "Пользователь с таким email не найден"


class ExportJobNotFoundException(AppException):
    status_code: int = 404
    detail: str = "Задача экспорта не найдена"
