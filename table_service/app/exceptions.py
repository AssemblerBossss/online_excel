from fastapi import status, HTTPException

# Пользователь не найден
UserNotFoundException = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
)

# Неверная почта или пароль
IncorrectEmailOrPasswordException = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST, detail="Неверная почта или пароль"
)

# Некорректный формат токена
InvalidTokenFormatException = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST, detail="Некорректный формат токена"
)

# Недостаточно прав
ForbiddenException = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав"
)

TokenInvalidFormatException = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Неверный формат токена. Ожидается 'Bearer <токен>'",
)

# Нет доступа к данной таблице
AccessDeniedException = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к данной таблице"
)

# Некорректные данные для данной строки
ValidationException = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Некорректные данные для данной строки",
)

# Не найдено
NotFoundException = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Not Found"
)

# Ошибка создания таблицы
CanNotCreateTableException = HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Не удалось создать таблицу",
)
