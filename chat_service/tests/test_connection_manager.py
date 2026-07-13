import asyncio
from unittest.mock import AsyncMock

from chat_service.app.core.connection_manager import ConnectionManager


async def main():
    manager = ConnectionManager()

    # --- Тест 1: подключение и раздача одному соединению ---
    ws1 = AsyncMock()
    await manager.connect("dima1@mail.ru", ws1)
    await manager.send_to_local("dima1@mail.ru", {"type": "test", "content": "hello"})
    ws1.send_json.assert_awaited_once_with({"type": "test", "content": "hello"})
    print("Тест 1 OK: одиночная доставка работает")

    # --- Тест 2: несколько вкладок одного пользователя получают одно и то же ---
    ws2 = AsyncMock()
    await manager.connect("dima1@mail.ru", ws2)  # вторая "вкладка" того же юзера
    await manager.send_to_local(
        "dima1@mail.ru", {"type": "test", "content": "broadcast"}
    )
    ws1.send_json.assert_awaited_with({"type": "test", "content": "broadcast"})
    ws2.send_json.assert_awaited_with({"type": "test", "content": "broadcast"})
    print("Тест 2 OK: рассылка на несколько соединений одного юзера работает")

    # --- Тест 3: сообщение чужому пользователю не долетает ---
    ws3 = AsyncMock()
    await manager.connect("dima4@mail.ru", ws3)
    await manager.send_to_local(
        "dima1@mail.ru", {"type": "test", "content": "only for dima1"}
    )
    ws3.send_json.assert_not_awaited()
    print("Тест 3 OK: изоляция между пользователями работает")

    # --- Тест 4: "мёртвое" соединение (ошибка при send_json) автоматически удаляется ---
    ws_dead = AsyncMock()
    ws_dead.send_json.side_effect = Exception("connection closed")
    await manager.connect("dima1@mail.ru", ws_dead)

    assert len(manager._connections["dima1@mail.ru"]) == 3  # ws1, ws2, ws_dead
    await manager.send_to_local("dima1@mail.ru", {"type": "test"})
    assert len(manager._connections["dima1@mail.ru"]) == 2  # ws_dead удалён
    assert ws_dead not in manager._connections["dima1@mail.ru"]
    print("Тест 4 OK: мёртвые соединения корректно вычищаются без RuntimeError")

    # --- Тест 5: явный disconnect убирает пользователя из словаря, если соединений не осталось ---
    manager.disconnect("dima4@mail.ru", ws3)
    assert "dima4@mail.ru" not in manager._connections
    print("Тест 5 OK: пустой email убирается из словаря целиком")

    print("\nВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО")


asyncio.run(main())
