FROM python:3.13-slim

WORKDIR /app

COPY auth_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY auth_service ./auth_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "auth_service.app.main:app", "--host", "0.0.0.0", "--port", "8080"]