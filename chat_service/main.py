from fastapi import FastAPI
from contextlib import asynccontextmanager
from chat_service.app.core.user_event_consumer import user_event_consumer
from chat_service.app.api.endpoints import chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await user_event_consumer.connect()
    yield
    # Shutdown
    await user_event_consumer.close()


app = FastAPI(lifespan=lifespan)

app.include_router(chat_router, prefix="/chat", tags=["Chat"])


@app.get("/health.", include_in_schema=False)
async def health_check():
    return {"status": "ok"}
