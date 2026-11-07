"""Android S3 的删除恢复与做菜安全重试契约。"""

from fastapi.testclient import TestClient


def auth_headers(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "S3-test-pass-482"},
    )
    assert response.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "S3-test-pass-482"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def create_ingredient(client: TestClient, headers: dict[str, str], quantity: str = "6.00") -> int:
    response = client.post(
        "/api/v1/ingredients",
        headers=headers,
        json={
            "name": "鸡蛋",
            "quantity": quantity,
            "unit": "个",
            "storage": "fridge",
            "expire_on": "2026-11-10",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def test_ingredient_and_shopping_item_can_be_restored(client: TestClient) -> None:
    headers = auth_headers(client, "pantry-s3-restore")
    ingredient_id = create_ingredient(client, headers)
    shopping_response = client.post(
        "/api/v1/shopping-items",
        headers=headers,
        json={"name": "番茄", "quantity": "2.00", "unit": "个"},
    )
    shopping_id = shopping_response.json()["data"]["id"]

    assert client.delete(f"/api/v1/ingredients/{ingredient_id}", headers=headers).status_code == 200
    deleted_shopping = client.delete(f"/api/v1/shopping-items/{shopping_id}", headers=headers)
    assert deleted_shopping.status_code == 200
    assert client.get("/api/v1/ingredients", headers=headers).json()["data"]["items"] == []
    assert client.get("/api/v1/shopping-items", headers=headers).json()["data"]["items"] == []

    restored_ingredient = client.post(
        f"/api/v1/ingredients/{ingredient_id}/restore", headers=headers
    )
    restored_shopping = client.post(
        f"/api/v1/shopping-items/{shopping_id}/restore", headers=headers
    )
    assert restored_ingredient.status_code == 200
    assert restored_ingredient.json()["data"]["quantity"] == "6.00"
    assert restored_shopping.status_code == 200
    assert restored_shopping.json()["data"]["name"] == "番茄"
    assert client.get("/api/v1/ingredients", headers=headers).json()["data"]["total"] == 1
    assert client.get("/api/v1/shopping-items", headers=headers).json()["data"]["total"] == 1


def test_restore_does_not_cross_user_boundary(client: TestClient) -> None:
    owner = auth_headers(client, "pantry-s3-owner")
    other = auth_headers(client, "pantry-s3-other")
    ingredient_id = create_ingredient(client, owner)
    assert client.delete(f"/api/v1/ingredients/{ingredient_id}", headers=owner).status_code == 200
    response = client.post(f"/api/v1/ingredients/{ingredient_id}/restore", headers=other)
    assert response.status_code == 404
    assert response.json()["code"] == 40401


def test_cook_replay_is_idempotent_and_changed_request_conflicts(client: TestClient) -> None:
    headers = auth_headers(client, "pantry-s3-cook")
    create_ingredient(client, headers)
    payload = {
        "recipe_name": "香葱炒蛋",
        "uses": [{"name": "鸡蛋", "quantity": "2.00", "unit": "个"}],
        "request_id": "android-s3-cook-0001",
    }

    first = client.post("/api/v1/pantry/cook", headers=headers, json=payload)
    replay = client.post("/api/v1/pantry/cook", headers=headers, json=payload)
    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["data"] == first.json()["data"]

    stock = client.get("/api/v1/ingredients", headers=headers).json()["data"]["items"]
    assert stock[0]["quantity"] == "4.00"

    changed = {**payload, "uses": [{"name": "鸡蛋", "quantity": "3.00", "unit": "个"}]}
    conflict = client.post("/api/v1/pantry/cook", headers=headers, json=changed)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == 40901
    stock_response = client.get("/api/v1/ingredients", headers=headers)
    stock_after_conflict = stock_response.json()["data"]["items"]
    assert stock_after_conflict[0]["quantity"] == "4.00"
