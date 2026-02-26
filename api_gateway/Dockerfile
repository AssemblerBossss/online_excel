FROM python:3.13-slim

WORKDIR /app

COPY api_gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY api_gateway ./api_gateway

ENV PYTHONPATH=/app

CMD ["uvicorn", "api_gateway.app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]