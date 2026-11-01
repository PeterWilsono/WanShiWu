"""收藏 CRUD、标签、用户隔离与 FTS5 搜索测试。"""

from fastapi.testclient import TestClient

PASSWORD = "correct-inbox-569"


def auth_headers(client: TestClient, username: str = "reader") -> tuple[dict[str, str], dict]:
    client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    )
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, response.json()["data"]


def create_bookmark(
    client: TestClient,
    headers: dict[str, str],
    url: str = "https://example.com/articles/life",
    **overrides,
):
    payload = {"url": url, "title": "生活效率指南", "tags": ["效率", "阅读"]}
    payload.update(overrides)
    return client.post("/api/v1/bookmarks", json=payload, headers=headers)


def test_create_normalizes_url_and_saves_manual_tags(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    response = create_bookmark(
        client,
        headers,
        url="HTTPS://Example.COM/articles/life#section",
        note="周末读完",
        tags=["效率", "效率", " 阅读 "],
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["url"] == "https://example.com/articles/life"
    assert data["source_domain"] == "example.com"
    assert data["status"] == "pending"
    assert data["note"] == "周末读完"
    assert {(tag["name"], tag["source"]) for tag in data["tags"]} == {
        ("效率", "manual"),
        ("阅读", "manual"),
    }

    tags = client.get("/api/v1/tags", headers=headers).json()["data"]["items"]
    assert [tag["name"] for tag in tags] == ["效率", "阅读"]

    duplicate = create_bookmark(client, headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["message"] == "这个链接已经收藏过了"


def test_list_filters_by_status_and_tag_with_pagination(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    create_bookmark(client, headers, "https://example.com/1", tags=["工作"])
    create_bookmark(client, headers, "https://example.com/2", tags=["生活"])
    create_bookmark(client, headers, "https://example.com/3", tags=["工作"])

    response = client.get(
        "/api/v1/bookmarks?tag=工作&status=pending&page=1&page_size=1", headers=headers
    )
    data = response.json()["data"]
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["tags"][0]["name"] == "工作"


def test_search_supports_chinese_english_and_short_query(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    create_bookmark(
        client,
        headers,
        "https://example.com/productivity",
        title="深度工作效率指南",
        note=None,
        tags=[],
    )
    bookmark_id = client.get("/api/v1/bookmarks", headers=headers).json()["data"]["items"][0]["id"]
    client.patch(
        f"/api/v1/bookmarks/{bookmark_id}",
        json={"title": "深度工作效率指南 productivity"},
        headers=headers,
    )

    for query in ["效率指", "productivity", "效"]:
        response = client.get(f"/api/v1/bookmarks/search?q={query}", headers=headers)
        assert response.status_code == 200
        assert response.json()["data"]["total"] == 1


def test_update_delete_and_restore_same_url_keeps_fts_consistent(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    bookmark_id = create_bookmark(client, headers).json()["data"]["id"]
    response = client.patch(
        f"/api/v1/bookmarks/{bookmark_id}",
        json={"title": "全新的阅读标题", "note": "已修改", "tags": ["新标签"]},
        headers=headers,
    )
    assert response.json()["data"]["title"] == "全新的阅读标题"
    assert [tag["name"] for tag in response.json()["data"]["tags"]] == ["新标签"]
    assert client.get(
        "/api/v1/bookmarks/search?q=全新的阅", headers=headers
    ).json()["data"]["total"] == 1

    assert client.delete(f"/api/v1/bookmarks/{bookmark_id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/bookmarks/{bookmark_id}", headers=headers).status_code == 404
    assert client.get(
        "/api/v1/bookmarks/search?q=全新的阅", headers=headers
    ).json()["data"]["total"] == 0

    restored = create_bookmark(client, headers, title="重新收藏", tags=["重来"])
    assert restored.status_code == 200
    assert restored.json()["data"]["id"] == bookmark_id
    assert restored.json()["data"]["title"] == "重新收藏"
    assert [tag["name"] for tag in restored.json()["data"]["tags"]] == ["重来"]


def test_bookmark_user_isolation_and_authentication(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    other_headers, _ = auth_headers(client, "other")
    bookmark_id = create_bookmark(client, headers).json()["data"]["id"]

    assert client.get(f"/api/v1/bookmarks/{bookmark_id}", headers=other_headers).status_code == 404
    assert client.patch(
        f"/api/v1/bookmarks/{bookmark_id}", json={"title": "越权"}, headers=other_headers
    ).status_code == 404
    assert (
        client.delete(f"/api/v1/bookmarks/{bookmark_id}", headers=other_headers).status_code
        == 404
    )
    assert client.get("/api/v1/bookmarks/search?q=生活效率", headers=other_headers).json()[
        "data"
    ]["total"] == 0
    assert client.get("/api/v1/bookmarks").status_code == 401


def test_bookmark_rejects_invalid_url_and_tags(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    for url in ["file:///tmp/a", "not-a-url", "https://user:pass@example.com/a"]:
        response = create_bookmark(client, headers, url)
        assert response.status_code == 422
    assert create_bookmark(client, headers, tags=["  "]).status_code == 422
    assert client.get("/api/v1/bookmarks/search?q=", headers=headers).status_code == 422
