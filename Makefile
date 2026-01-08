run:
		docker compose down && \
		docker compose build frontend && \
		docker compose up -d && \
		sleep 5 && \
		alembic upgrade head && \
		uvicorn backend.app.main:app  --reload