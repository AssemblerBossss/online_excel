import httpx
import pytest

pytestmark = pytest.mark.integration


async def _create_table(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
    **overrides,
) -> int:
    response = await http_client.post(
        "/tables/create",
        json=make_table_payload(**overrides),
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_row(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    table_id: int,
    row_data: dict,
) -> dict:
    response = await http_client.post(
        f"/data/{table_id}/rows",
        json={"row_data": row_data},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_list_row_require_authentification(http_client: httpx.AsyncClient):
    response = await http_client.get("/data/1/rows")
    assert response.status_code == 401


async def test_create_row_requires_authentication(http_client: httpx.AsyncClient):
    response = await http_client.post("/data/1/rows", json={"row_data": {"a": 1}})
    assert response.status_code == 401


async def test_get_rows_for_unknown_table_returns_404(
    http_client: httpx.AsyncClient, auth_headers: dict[str, str]
):
    response = await http_client.get("/data/00009999/rows", headers=auth_headers)
    assert response.status_code == 404


async def test_create_row_returns_201_with_payload(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)

    response = await http_client.post(
        f"/data/{table_id}/rows",
        json={"row_data": {"name": "Alice", "age": 30}},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["table_id"] == table_id
    assert body["row_data"] == {"name": "Alice", "age": 30}
    assert isinstance(body["id"], int)
    assert "created_at" in body


async def test_created_row_appears_in_list(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)
    created = await _create_row(http_client, auth_headers, table_id, {"name": "Bob"})

    list_response = await http_client.get(
        f"/data/{table_id}/rows", headers=auth_headers
    )

    assert list_response.status_code == 200
    rows = list_response.json()
    assert created["id"] in [r["id"] for r in rows]


async def test_get_row_by_id_returns_created_row(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)
    created = await _create_row(
        http_client, auth_headers, table_id, {"name": "Charlie"}
    )

    response = await http_client.get(
        f"/data/{table_id}/rows/{created['id']}", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["row_data"] == {"name": "Charlie"}


async def test_get_unknown_row_returns_404(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)

    response = await http_client.get(
        f"/data/{table_id}/rows/99999999", headers=auth_headers
    )
    assert response.status_code == 404


async def test_update_row_changes_data(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)
    created = await _create_row(
        http_client, auth_headers, table_id, {"name": "Dave", "age": 20}
    )

    response = await http_client.put(
        f"/data/{table_id}/rows/{created['id']}",
        json={"row_data": {"name": "Dave", "age": 21}},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == created["id"]
    assert body["row_data"]["age"] == 21


async def test_update_unknown_row_returns_404(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)

    response = await http_client.put(
        f"/data/{table_id}/rows/99999999",
        json={"row_data": {"name": "ghost"}},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_delete_row_returns_204_and_removes_it(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)
    created = await _create_row(http_client, auth_headers, table_id, {"name": "Eve"})

    delete_response = await http_client.delete(
        f"/data/{table_id}/rows/{created['id']}", headers=auth_headers
    )
    assert delete_response.status_code == 204

    get_response = await http_client.get(
        f"/data/{table_id}/rows/{created['id']}", headers=auth_headers
    )
    assert get_response.status_code == 404


async def test_delete_unknown_row_returns_404(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)

    response = await http_client.delete(
        f"/data/{table_id}/rows/99999999", headers=auth_headers
    )
    assert response.status_code == 404


async def test_create_row_violating_schema_returns_422(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(
        http_client,
        auth_headers,
        make_table_payload,
        columns_schema=[{"name": "name", "type": "string"}],
    )

    response = await http_client.post(
        f"/data/{table_id}/rows",
        json={"row_data": {"name": 12345}},
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text


async def test_create_row_missing_required_field_returns_422(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(
        http_client,
        auth_headers,
        make_table_payload,
        columns_schema=[{"name": "email", "type": "string", "required": True}],
    )

    response = await http_client.post(
        f"/data/{table_id}/rows",
        json={"row_data": {"other": "value"}},
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text


async def test_list_rows_supports_pagination(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)
    for i in range(3):
        await _create_row(http_client, auth_headers, table_id, {"i": i})

    response = await http_client.get(
        f"/data/{table_id}/rows",
        params={"skip": 0, "limit": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_rows_rejects_invalid_limit(
    http_client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    make_table_payload,
):
    table_id = await _create_table(http_client, auth_headers, make_table_payload)

    response = await http_client.get(
        f"/data/{table_id}/rows",
        params={"limit": 0},
        headers=auth_headers,
    )
    assert response.status_code == 422
