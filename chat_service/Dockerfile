FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY chat_service/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY chat_service ./chat_service

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "chat_service.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]

