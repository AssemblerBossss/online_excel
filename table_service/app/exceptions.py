class AppException(Exception):
    """Базовое доменное исключение."""

    detail: str = "Internal server error"

    def __init__(self, detail: str = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class AccessDeniedException(AppException):
    detail = "Нет доступа к данной таблице"


class ValidationException(AppException):
    detail = "Ошибка валидации данных"


class NotFoundException(AppException):
    detail = "Not Found"


class CanNotCreateTableException(AppException):
    detail = "Не удалось создать таблицу"


class CanNotDeleteTableException(AppException):
    detail = "Не удалось удалить таблицу"


class ForbiddenException(AppException):
    detail = "Недостаточно прав"


class TokenInvalidFormatException(AppException):
    detail = "Неверный формат токена. Ожидается 'Bearer <токен>'"


class InvalidWSTicketException(AppException):
    detail = "Недействительный или истёкший WebSocket-тикет"


class InvalidFileFormatException(AppException):
    detail = "Неверный формат файла"


class InvalidFileMimeTypeException(AppException):
    detail = "Неподдерживаемый тип файла"


class EmptyFileException(AppException):
    detail = "Файл пустой"


class FileParseException(AppException):
    detail = "Ошибка парсинга файла"


class CanNotUpdateTableException(AppException):
    detail = "Ошибка обновления таблицы"


class PermissionAlreadyExistsException(AppException):
    detail = "Права для этого пользователя уже существуют"


class CanNotCreatePermissionException(AppException):
    detail = "Не удалось создать права доступа"


class ExportJobNotFoundException(AppException):
    pass
