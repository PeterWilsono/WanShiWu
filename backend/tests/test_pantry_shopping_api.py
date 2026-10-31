"""购物清单 CRUD、筛选、参数校验、认证与用户隔离测试。"""

from fastapi.testclient import TestClient

PASSWORD = "correct-shopping-361"


def auth_headers(client: TestClient, username: str = "shopping-api") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_item(
    client: TestClient, headers: dict[str, str], name: str = "牛奶", **overrides: object
) -> dict:
    response = client.post(
        "/api/v1/shopping-items",
        headers=headers,
        json={"name": name, "quantity": "1.5", "unit": "升", **overrides},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_shopping_create_defaults_and_list_filters(client: TestClient) -> None:
    headers = auth_headers(client)
    manual = create_item(client, headers)
    recipe = create_item(
        client,
        headers,
        name="番茄",
        quantity="3",
        unit="个",
        source="recipe",
        recipe_name="番茄炒蛋",
    )

    assert manual["done"] is False and manual["source"] == "manual"
    assert manual["quantity"] == "1.50" and recipe["recipe_name"] == "番茄炒蛋"
    pending = client.get("/api/v1/shopping-items", headers=headers, params={"done": False})
    assert pending.json()["data"]["total"] == 2
    from_recipe = client.get("/api/v1/shopping-items", headers=headers, params={"source": "recipe"})
    assert [item["id"] for item in from_recipe.json()["data"]["items"]] == [recipe["id"]]


def test_shopping_patch_supports_done_and_explicit_null(client: TestClient) -> None:
    headers = auth_headers(client)
    item = create_item(client, headers)

    response = client.patch(
        f"/api/v1/shopping-items/{item['id']}",
        headers=headers,
        json={"done": True, "quantity": None, "unit": None},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["done"] is True and data["quantity"] is None and data["unit"] is None

    done_items = client.get("/api/v1/shopping-items", headers=headers, params={"done": True})
    assert done_items.json()["data"]["total"] == 1
    pending_items = client.get("/api/v1/shopping-items", headers=headers, params={"done": False})
    assert pending_items.json()["data"]["total"] == 0


def test_shopping_delete_and_user_isolation(client: TestClient) -> None:
    headers = auth_headers(client)
    other_headers = auth_headers(client, "shopping-other")
    item = create_item(client, headers)

    forbidden = client.patch(
        f"/api/v1/shopping-items/{item['id']}", headers=other_headers, json={"done": True}
    )
    assert forbidden.status_code == 404 and forbidden.json()["code"] == 40401
    assert client.delete(f"/api/v1/shopping-items/{item['id']}", headers=headers).status_code == 200
    assert client.delete(f"/api/v1/shopping-items/{item['id']}", headers=headers).status_code == 404
    assert client.get("/api/v1/shopping-items", headers=headers).json()["data"]["total"] == 0


def test_shopping_validation_and_authentication(client: TestClient) -> None:
    headers = auth_headers(client)
    invalid = client.post(
        "/api/v1/shopping-items",
        headers=headers,
        json={"name": "  ", "quantity": 0, "unit": "箱"},
    )
    assert invalid.status_code == 422 and invalid.json()["code"] == 40001
    assert client.get("/api/v1/shopping-items").status_code == 401
    assert client.post("/api/v1/shopping-items", json={"name": "牛奶"}).status_code == 401
