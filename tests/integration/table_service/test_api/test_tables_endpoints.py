import uuid

import httpx
import pytest


pytestmark = pytest.mark.integration


async def test_get_tables_requires_authentication(http_client: httpx.AsyncClient):
    response = await http_client.get("/tables")
    assert response.status_code == 401


async def test_get_tables_with_invalid_token_returns_401(
    http_client: httpx.AsyncClient,
):
    response = await http_client.get(
        "/tables",
        headers={"Authorization": "Bearer not.a.real.jwt"},
    )
    assert response.status_code == 401


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
