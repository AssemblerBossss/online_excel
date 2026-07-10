FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY table_service/requirements.txt ./

RUN pip install --no-cache-dir --no-compile -r requirements.txt \
  && pip uninstall -y pip \
  && find /opt/venv -name '__pycache__' -type d -exec rm -rf {} \;

# ЭТАП 2: Финальный образ (Runtime)
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

# Создаем non-root пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Копируем ТОЛЬКО готовое виртуальное окружение из этапа 1
COPY --from=builder /opt/venv /opt/venv

COPY --chown=appuser:appuser table_service ./table_service

USER appuser

EXPOSE 8000

CMD ["uvicorn", "table_service.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]