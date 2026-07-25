import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chat_service.app.api.endpoints import chat_router, ws_router
from chat_service.app.core.es_client import es_client
from chat_service.app.core.realtime import dispatch_event, redis_pubsub
from chat_service.app.core.user_event_consumer import user_event_consumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    await user_event_consumer.connect()
    await redis_pubsub.connect()
    await es_client.ensure_index()
    listener_task = asyncio.create_task(redis_pubsub.listen(dispatch_event))

    yield

    listener_task.cancel()
    await redis_pubsub.close()
    await user_event_consumer.close()
    await es_client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(ws_router, prefix="/chat", tags=["Chat WS"])


@app.get("/health/", include_in_schema=False)
async def health_check():
    return {"status": "ok"}
