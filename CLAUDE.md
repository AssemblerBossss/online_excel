# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`online_excel` turns shared Excel files into a multi-user web database: users define table templates, upload Excel data into them, and work with the rows through a web UI. It is a **microservices** system, not a single backend.

## Architecture

Three Python/FastAPI services plus a React frontend, wired together with docker-compose. All external traffic goes through the API Gateway; the two backend services are never called directly by the frontend.

```
frontend (React/Vite, :3000)
        │  /api/*
        ▼
api_gateway (:8080)  ── JWT auth, rate limit, circuit breaker, request logging
   ├─ /auth/*, /users/*  ──► auth_service  (:8001)  ──► auth_db (Postgres :8010)
   └─ /tables/*, /data/*, /search  ──► table_service (:8000) ──► db (Postgres :7777)
```

- **api_gateway/** — Reverse proxy. `routers/proxy.py` forwards path prefixes to the right service; `circuit_breaker.py` wraps each upstream (aiobreaker); `middleware/` does JWT validation, slowapi rate limiting, request size limits, and logging. The gateway owns auth at the edge — backend services largely trust the forwarded request.
- **auth_service/** — Users, registration/login, JWT issue/refresh, avatar upload to **MinIO** (S3). On every user change it **publishes** an event to RabbitMQ (`events/publisher.py`, topic exchange `user.events`, routing keys `user.registered` / `user.updated` / `user.deleted`).
- **table_service/** — Tables, rows ("data"), Excel import/export, permissions, and full-text **search via Elasticsearch**. Caches reads in Redis (fastapi-cache2). It does **not** call auth_service for user data; instead it **consumes** the `user.events` stream (`core/user_event_consumer.py`) and maintains a local read-model copy of users in the `user_projection` table. This is event-driven CQRS: a freshly registered user can hit a small delay before table_service knows about them (integration tests poll `/tables` until the projection syncs).

### table_service internal layering

`api/endpoints` (FastAPI routers) → `services/` (business logic, raises domain exceptions from `exceptions.py`) → `repository/` (pure SQLAlchemy data access, no business logic) → `models/`. Domain exceptions are mapped to HTTP status codes centrally in `main.py:register_exception_handlers`. Keep business logic out of repositories and let services raise custom exceptions rather than returning error states.

## Landmines (read before editing)

- **`auth_service/app/сore/` is spelled with a Cyrillic `с`**, not Latin `core`. Imports read `from auth_service.app.сore import ...`. If an import "looks right but fails," check for the homoglyph. (table_service uses a normal Latin `core/`.)
- **The root `alembic/` and `Makefile` are stale relics** from before the service split — `alembic/env.py` and the Makefile import a `backend.app.*` package that no longer exists. Do **not** run `alembic upgrade` or `make run`. Schema is created at startup by each service via `Base.metadata.create_all` inside its `init_db()` (`*/app/*ore/database.py`). Don't add a migration step expecting the root alembic to work.
- **Each service has its own dependencies** (`<service>/requirements.txt`) and its own Postgres DB. The root `pyproject.toml`/`poetry.lock` is the superset for local tooling; CI installs per-service requirements.
- **table_service config uses a prefixed env scheme**: pydantic-settings with `env_prefix="EXCEL_APP__"` and `env_nested_delimiter="__"`, so its env vars look like `EXCEL_APP__DB_HOST`. auth_service and api_gateway use plain names (`DB_HOST`, `JWT_SECRET_KEY`, …). docker-compose maps both.

## Commands

### Run the whole stack
```bash
docker compose up -d --wait        # all services + Postgres x2, Redis, RabbitMQ, Elasticsearch, MinIO
docker compose logs -f <service>   # e.g. table_service, auth_service, api_gateway
docker compose down                # add -v to wipe volumes/data
```
Local defaults are baked into `docker-compose.yaml` (e.g. `JWT_SECRET_KEY=local_dev_secret`); in CI/prod these come from secrets. UIs: RabbitMQ `:15672`, MinIO console `:9001`.

### Frontend
```bash
cd frontend
npm install
npm run dev        # Vite dev server
npm run build      # production build (also built via frontend/Dockerfile + nginx)
```

### Lint / format (per service, matches CI — Ruff, default config)
```bash
cd <service>          # api_gateway | auth_service | table_service
ruff check .
ruff format --check . # drop --check to auto-format
```

### Tests
Run from the **repo root** (tests import `table_service.app.*`, `auth_service.app.*`, etc., so the root must be importable). Config lives in `tests/pytest.ini` (`asyncio_mode=auto`).

```bash
# Unit tests for one service (install that service's requirements first)
pytest tests/unit/table_service
pytest tests/unit/auth_service
pytest tests/unit/api_gateway

# A single test
pytest tests/unit/table_service/test_services/test_<x>.py::test_<name> -v

# Integration tests — require the full docker stack to be up and healthy.
# They talk to the running gateway (GATEWAY_URL, default http://localhost:8080).
docker compose up -d --wait
pytest tests/integration -m integration -v
```

`tests/` is organized as `unit/<service>/…`, `integration/<service>/…`, and `e2e/`. The `integration` pytest marker gates tests that need the live compose stack.

## CI

`.github/workflows/ci-<service>.yml` run on changes under each service path: Ruff lint + format check, then per-service unit tests (table_service also uploads coverage to Codecov). `сi-integration-tests.yaml` triggers **after** the per-service workflows succeed, spins up the full compose stack with `--wait`, and runs `tests/integration -m integration`.

## API collection

`online_api_collection/` holds request definitions (register/login/refresh/logout, table CRUD, search) usable as live examples of the gateway's request/response shapes.