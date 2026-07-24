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
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    payload = make_table_payload(
        description="Integration test table",
        columns_schema=[
            {"name": "id", "type": "integer"},
            {"name": "amount", "type": "float"},
        ],
    )
    response = await http_client.post(
        "/tables/create", json=payload, headers=auth_headers
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["name"] == payload["name"]
    assert body["description"] == payload["description"]
    assert body["is_public"] is False
    assert isinstance(body["id"], int)


async def test_created_table_appears_in_list(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    create_response = await http_client.post(
        "/tables/create",
        json=make_table_payload(is_public=True),
        headers=auth_headers,
    )
    created_id = create_response.json()["id"]

    list_response = await http_client.get("/tables", headers=auth_headers)
    assert list_response.status_code == 200
    assert created_id in [t["id"] for t in list_response.json()]


async def test_get_table_by_id_returns_created_table(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    create_response = await http_client.post(
        "/tables/create", json=make_table_payload(), headers=auth_headers
    )
    table_id = create_response.json()["id"]

    response = await http_client.get(f"/tables/{table_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == table_id


async def test_get_unknown_table_returns_404(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
):
    response = await http_client.get("/tables/99999999", headers=auth_headers)
    assert response.status_code == 404


async def test_patch_table_updates_fields(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    create_response = await http_client.post(
        "/tables/create",
        json=make_table_payload(description="old"),
        headers=auth_headers,
    )
    table_id = create_response.json()["id"]

    patch_response = await http_client.patch(
        f"/tables/{table_id}",
        json={"description": "updated", "is_public": True},
        headers=auth_headers,
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["description"] == "updated"
    assert body["is_public"] is True


async def test_delete_table_returns_204_and_removes_it(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    create_response = await http_client.post(
        "/tables/create", json=make_table_payload(), headers=auth_headers
    )
    table_id = create_response.json()["id"]

    delete_response = await http_client.delete(
        f"/tables/delete/{table_id}", headers=auth_headers
    )
    assert delete_response.status_code == 204

    get_response = await http_client.get(f"/tables/{table_id}", headers=auth_headers)
    assert get_response.status_code == 404
