import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from chat_service.app.api.endpoints import chat_router, ws_router
from chat_service.app.core.es_client import es_client
from chat_service.app.core.realtime import dispatch_event, redis_pubsub
from chat_service.app.core.user_event_consumer import user_event_consumer
from chat_service.app.exceptions import ChatException


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


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(ChatException)
    async def chat_exception_handler(request: Request, exc: ChatException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(ChatException)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": str(exc)})


app = FastAPI(lifespan=lifespan)

app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(ws_router, prefix="/chat", tags=["Chat WS"])


@app.get("/health/", include_in_schema=False)
async def health_check():
    return {"status": "ok"}
