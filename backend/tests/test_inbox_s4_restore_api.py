"""Android S4 收藏删除恢复与全文索引契约。"""

from fastapi.testclient import TestClient


def auth_headers(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "S4-test-pass-482"},
    )
    assert response.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "S4-test-pass-482"},
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def test_restore_bookmark_also_restores_search_index(client: TestClient) -> None:
    headers = auth_headers(client, "inbox-s4-restore")
    created = client.post(
        "/api/v1/bookmarks",
        headers=headers,
        json={
            "url": "https://example.com/inbox-s4",
            "title": "独特的收藏恢复标题",
            "tags": ["阅读"],
        },
    )
    assert created.status_code == 200
    bookmark_id = created.json()["data"]["id"]
    assert client.delete(f"/api/v1/bookmarks/{bookmark_id}", headers=headers).status_code == 200
    assert client.get("/api/v1/bookmarks", headers=headers).json()["data"]["items"] == []
    deleted_search = client.get("/api/v1/bookmarks/search?q=独特的收藏恢复标题", headers=headers)
    assert deleted_search.json()["data"]["items"] == []

    restored = client.post(f"/api/v1/bookmarks/{bookmark_id}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["data"]["title"] == "独特的收藏恢复标题"
    assert restored.json()["data"]["tags"][0]["name"] == "阅读"
    search = client.get("/api/v1/bookmarks/search?q=独特的收藏恢复标题", headers=headers)
    assert search.status_code == 200
    assert search.json()["data"]["total"] == 1


def test_restore_bookmark_does_not_cross_user_boundary(client: TestClient) -> None:
    owner = auth_headers(client, "inbox-s4-owner")
    other = auth_headers(client, "inbox-s4-other")
    created = client.post(
        "/api/v1/bookmarks", headers=owner, json={"url": "https://example.com/private-s4"}
    )
    bookmark_id = created.json()["data"]["id"]
    assert client.delete(f"/api/v1/bookmarks/{bookmark_id}", headers=owner).status_code == 200
    response = client.post(f"/api/v1/bookmarks/{bookmark_id}/restore", headers=other)
    assert response.status_code == 404
    assert response.json()["code"] == 40401
