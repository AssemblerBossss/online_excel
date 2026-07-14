FROM python:3.13-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY auth_service/requirements.txt ./

RUN pip install --no-cache-dir --no-compile -r requirements.txt \
  && pip uninstall -y pip \
  && find /opt/venv -name '__pycache__' -type d -exec rm -rf {} \;

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY  auth_service ./auth_service

CMD ["uvicorn", "auth_service.app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]