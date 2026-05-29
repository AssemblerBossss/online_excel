# API Tracker (бэкенд ↔ фронтенд)

Трекер для отслеживания: какие ручки реализованы в бэкенде и какие соответствующие
функции нужно добавить во фронтенд (`frontend/src/api/*.ts`).

**Легенда статуса:** ⬜ TODO · 🟡 в работе · ✅ готово

> Здесь перечислены **только новые предложенные ручки** (ещё не реализованы).
> Уже существующие эндпоинты сюда не вносятся.

## auth_service — `/users`

| Метод и путь | Назначение | Бэкенд | Фронт-функция (`api/users.ts`) | Фронт |
|---|---|---|---|---|
| `PATCH /users/{user_id}` | Обновление профиля (first_name, last_name, email). Публикует `user.updated`. | ⬜ | `updateUser(userId, payload)` | ⬜ |
| `POST /users/{user_id}/activate` | Активация пользователя (симметрично deactivate). | ⬜ | `activateUser(userId)` | ⬜ |
| `PATCH /users/{user_id}/role` | Смена роли пользователя (только admin). Публикует `user.updated`. | ⬜ | `updateUserRole(userId, role)` | ⬜ |
| `DELETE /users/{user_id}/avatar` | Удалить/сбросить аватар (default-avatar). | ⬜ | `deleteAvatar(userId)` | ⬜ |

## auth_service — `/users/me` и сессии

| Метод и путь | Назначение | Бэкенд | Фронт-функция (`api/auth.ts` / `users.ts`) | Фронт |
|---|---|---|---|---|
| `POST /users/me/change-password` | Смена пароля (old_password + new + confirm). | ⬜ | `changePassword(payload)` | ⬜ |
| `GET /users/me/sessions` | Список активных сессий (user_agent, ip, created_at). | ⬜ | `getSessions()` | ⬜ |
| `DELETE /users/me/sessions` | Ревокнуть все refresh-токены («выйти со всех устройств»). | ⬜ | `revokeAllSessions()` | ⬜ |