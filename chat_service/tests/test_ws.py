import asyncio

import websockets


async def main():
    ticket = input("Вставьте тикет: ")
    uri = f"ws://127.0.0.1:8002/chat/ws?ticket={ticket}"
    async with websockets.connect(uri) as ws:
        print("Подключено, жду события...")
        async for message in ws:
            print("Получено событие:", message)


asyncio.run(main())
