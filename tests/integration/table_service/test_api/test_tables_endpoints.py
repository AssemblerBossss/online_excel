import os
import uuid

import httpx
import asyncio
import pytest


pytestmark = pytest.mark.integration

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")
# Запас на пропагацию UserCreated через RabbitMQ в table_service.user_projection
USER_SYNC_TIMEOUT = 10.0


def _unique_email() -> str:
    return f"table_it_{uuid.uuid4().hex[:10]}@test.local"


@pytest.fixture(scope="module")
async def http_client():
    async with httpx.AsyncClient(
        base_url=GATEWAY_URL, timeout=USER_SYNC_TIMEOUT
    ) as client:
        yield client


async def _register_and_login(client: httpx.AsyncClient) -> tuple[str, str]:
    """Регистрирует нового пользователя, возвращает (email, access_token)."""
    email = _unique_email()
    password = "Test_Pass_123"
    register_payload = {
        "email": email,
        "first_name": "Test",
        "last_name": "User",
        "password": password,
        "confirm_password": password,
    }
    register_response = await client.post("/auth/register", json=register_payload)
    assert register_response.status_code == 201, register_response.text

    login_response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text
    return email, login_response.json()["access_token"]


async def _wait_user_synced(client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    """
    UserProjection в table_service обновляется через RabbitMQ.
    Считаем пользователя синхронизированным, когда /tables отдаёт 200.
    """

    deadline = asyncio.get_event_loop().time() + USER_SYNC_TIMEOUT
    last_status = None
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get("/tables", headers=headers)
        last_status = response.status_code
        if response.status_code == 200:
            return
        await asyncio.sleep(0.5)
    pytest.fail(
        f"User projection not synced in {USER_SYNC_TIMEOUT}s, last status={last_status}"
    )


@pytest.fixture
async def auth_headers(http_client: httpx.AsyncClient) -> dict[str, str]:
    _, access_token = await _register_and_login(http_client)
    headers = {"Authorization": f"Bearer {access_token}"}
    await _wait_user_synced(http_client, headers)
    return headers


async def test_get_tables_requires_authentication(http_client: httpx.AsyncClient):
    response = await http_client.get("/tables")
    assert response.status_code == 401
    assert "detail" in response.json()


async def test_create_table_returns_201_with_payload(
    http_client: httpx.AsyncClient, auth_headers: dict[str, str]
):
    payload = {
        "name": f"sales_{uuid.uuid4().hex[:6]}",
        "description": "Integration test table",
        "is_public": False,
        "columns_schema": [
            {"name": "id", "type": "integer"},
            {"name": "amount", "type": "float"},
        ],
    }

    response = await http_client.post(
        "/tables/create", json=payload, headers=auth_headers
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["name"] == payload["name"]
    assert body["description"] == payload["description"]
    assert body["is_public"] == payload["is_public"]
    assert isinstance(body["id"], int)
    assert "created_at" in body and "created_by" in body


async def test_created_table_appears_in_list(
    http_client: httpx.AsyncClient, auth_headers: dict[str, str]
):
    name = f"in_list_{uuid.uuid4().hex[:6]}"
    create_response = await http_client.post(
        "/tables/create",
        json={"name": name, "description": "x", "is_public": True},
        headers=auth_headers,
    )

    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    list_response = await http_client.get("/tables", headers=auth_headers)
    assert list_response.status_code == 200
    ids = [t["id"] for t in list_response.json()]
    assert created_id in ids


async def test_get_table_by_id_returns_created_table(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
):
    create_response = await http_client.post(
        "/tables/create",
        json={"name": f"get_by_id_{uuid.uuid4().hex[:6]}", "is_public": False},
        headers=auth_headers,
    )
    table_id = create_response.json()["id"]

    response = await http_client.get(f"/tables/{table_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == table_id


async def test_get_unknown_table_returns_404(
    http_client: httpx.AsyncClient, auth_headers: dict[str, str]
):
    response = await http_client.get("/tables/99999999", headers=auth_headers)
    assert response.status_code == 404


async def test_patch_table_updates_fields(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
):
    create_response = await http_client.post(
        "/tables/create",
        json={"name": f"patch_{uuid.uuid4().hex[:6]}", "description": "old"},
        headers=auth_headers,
    )
    table_id = create_response.json()["id"]

    new_description = "updated description"
    patch_response = await http_client.patch(
        f"/tables/{table_id}",
        json={"description": new_description, "is_public": True},
        headers=auth_headers,
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["id"] == table_id
    assert body["description"] == new_description
    assert body["is_public"] is True


async def test_delete_table_returns_204_and_removes_it(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
):

    create_response = await http_client.post(
        "/tables/create",
        json={"name": f"delete_{uuid.uuid4().hex[:6]}"},
        headers=auth_headers,
    )

    table_id = create_response.json()["id"]

    delete_response = await http_client.delete(
        f"/tables/delete{table_id}", headers=auth_headers
    )
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = await http_client.get(f"/tables/{table_id}", headers=auth_headers)
    assert get_response.status_code == 404
