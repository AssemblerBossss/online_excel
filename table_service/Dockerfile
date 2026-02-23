FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY table_service/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY table_service ./table_service

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "table_service.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-config=None"]

