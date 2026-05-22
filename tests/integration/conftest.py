import asyncio
import os
import uuid

import httpx
import pytest
import pytest_asyncio


GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")
USER_SYNC_TIMEOUT = 10.0


@pytest_asyncio.fixture(scope="session")
async def http_client():
    """HTTP-клиент для интеграционных тестов через api_gateway."""
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        yield client


async def _register_and_login(client: httpx.AsyncClient) -> str:
    """Регистрирует уникального пользователя и возвращает access_token."""
    email = f"it_{uuid.uuid4().hex[:10]}@test.local"
    password = "Test_Pass_123"

    register_response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "first_name": "Test",
            "last_name": "User",
            "password": password,
            "confirm_password": password,
        },
    )
    assert register_response.status_code == 201, register_response.text

    login_response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text
    return login_response.json()["access_token"]


async def _wait_user_synced(client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    """Ждём, пока UserCreated проедет через RabbitMQ в table_service."""
    deadline = asyncio.get_event_loop().time() + USER_SYNC_TIMEOUT
    last_status = None
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get("/tables", headers=headers)
        last_status = response.status_code
        if response.status_code == 200:
            return
        await asyncio.sleep(0.5)
    raise RuntimeError(
        f"User projection not synced in {USER_SYNC_TIMEOUT}s, last status={last_status}"
    )


@pytest_asyncio.fixture(scope="session")
async def auth_headers(http_client: httpx.AsyncClient) -> dict[str, str]:
    """Один зарегистрированный пользователь на всю сессию — обходит rate limit."""
    access_token = await _register_and_login(http_client)
    headers = {"Authorization": f"Bearer {access_token}"}
    await _wait_user_synced(http_client, headers)
    return headers


@pytest.fixture
def make_table_payload():
    """Фабрика payload'ов для create — каждый тест получает уникальное имя."""

    def _factory(**overrides) -> dict:
        payload = {
            "name": f"t_{uuid.uuid4().hex[:8]}",
            "description": "integration test",
            "is_public": False,
        }
        payload.update(overrides)
        return payload

    return _factory
