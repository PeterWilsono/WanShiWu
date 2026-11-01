"""收藏后台抓取、AI 摘要与手动正文兜底测试。"""

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.assistant.dependencies import get_llm_client
from app.llm.client import LLMResult
from app.llm.fake import FakeLLMClient
from app.main import app
from app.modules.inbox.ai_service import process_bookmark
from app.modules.inbox.fetcher import FetchedArticle, FetchError
from app.modules.inbox.models import Bookmark

PASSWORD = "correct-inbox-ai-569"


def auth_headers(client: TestClient, username: str = "ai-reader") -> tuple[dict[str, str], int]:
    client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})
    login = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    user_id = client.get("/api/v1/auth/me", headers=headers).json()["data"]["id"]
    return headers, user_id


def result(payload: dict | str) -> LLMResult:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return LLMResult(text, [], 10, 5, 20)


def create(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/bookmarks",
        json={"url": "https://example.com/article", "tags": ["手动"]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "pending"
    return response.json()["data"]["id"]


def session_factory(db_session: Session):
    return sessionmaker(bind=db_session.bind, expire_on_commit=False)


def test_background_process_saves_content_summary_and_ai_tags(
    client: TestClient, db_session: Session
) -> None:
    headers, user_id = auth_headers(client)
    bookmark_id = create(client, headers)
    llm = FakeLLMClient([result({"summary": "一篇测试摘要", "tags": ["技术", "手动"]})])
    long_content = "正文" * 4000 + "不应发送的尾标记"

    process_bookmark(
        bookmark_id,
        user_id,
        session_factory=session_factory(db_session),
        llm_factory=lambda db, uid: llm,
        fetcher=lambda url: FetchedArticle(title="抓取标题", content=long_content),
    )
    db_session.expire_all()
    data = client.get(f"/api/v1/bookmarks/{bookmark_id}", headers=headers).json()["data"]
    assert data["status"] == "success"
    assert data["title"] == "抓取标题"
    assert data["summary"] == "一篇测试摘要"
    assert data["content"] == long_content
    assert data["fetched_at"] is not None
    assert {(tag["name"], tag["source"]) for tag in data["tags"]} == {
        ("手动", "manual"),
        ("技术", "ai"),
    }
    assert "不可信" in llm.calls[0]["messages"][0]["content"]
    article_prompt = llm.calls[0]["messages"][1]["content"]
    assert long_content[:8000] in article_prompt
    assert long_content[8000:] not in article_prompt


def test_invalid_summary_is_retried_once(client: TestClient, db_session: Session) -> None:
    headers, user_id = auth_headers(client)
    bookmark_id = create(client, headers)
    llm = FakeLLMClient(
        [result("not-json"), result({"summary": "修正后的摘要", "tags": ["阅读"]})]
    )
    process_bookmark(
        bookmark_id,
        user_id,
        session_factory=session_factory(db_session),
        llm_factory=lambda db, uid: llm,
        fetcher=lambda url: FetchedArticle(title="标题", content="正文"),
    )
    db_session.expire_all()
    data = client.get(f"/api/v1/bookmarks/{bookmark_id}", headers=headers).json()["data"]
    assert data["status"] == "success"
    assert data["summary"] == "修正后的摘要"
    assert len(llm.calls) == 2


def test_fetch_failure_marks_failed_without_real_network(
    client: TestClient, db_session: Session
) -> None:
    headers, user_id = auth_headers(client)
    bookmark_id = create(client, headers)

    def fail_fetch(url: str):
        raise FetchError("网页抓取超时")

    process_bookmark(
        bookmark_id,
        user_id,
        session_factory=session_factory(db_session),
        llm_factory=lambda db, uid: FakeLLMClient(),
        fetcher=fail_fetch,
    )
    db_session.expire_all()
    data = client.get(f"/api/v1/bookmarks/{bookmark_id}", headers=headers).json()["data"]
    assert data["status"] == "failed"
    assert data["fail_reason"].startswith("网页抓取超时")

    retry = client.post(f"/api/v1/bookmarks/{bookmark_id}/retry", headers=headers)
    assert retry.status_code == 200
    assert retry.json()["data"]["status"] == "pending"


def test_manual_content_regenerates_summary(client: TestClient, db_session: Session) -> None:
    headers, user_id = auth_headers(client)
    bookmark_id = create(client, headers)
    bookmark = db_session.get(Bookmark, bookmark_id)
    bookmark.status = "failed"
    db_session.commit()
    llm = FakeLLMClient([result({"summary": "手动正文摘要", "tags": ["手动修复"]})])
    app.dependency_overrides[get_llm_client] = lambda: llm

    response = client.put(
        f"/api/v1/bookmarks/{bookmark_id}/content",
        json={"content": "这是用户手动粘贴的正文"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "success"
    assert data["summary"] == "手动正文摘要"
    assert data["content"] == "这是用户手动粘贴的正文"
    assert [tag["name"] for tag in data["tags"] if tag["source"] == "ai"] == ["手动修复"]
    assert client.get("/api/v1/bookmarks/search?q=手动粘贴", headers=headers).json()[
        "data"
    ]["total"] == 1


def test_manual_content_can_be_saved_without_calling_ai(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    bookmark_id = create(client, headers)
    llm = FakeLLMClient()
    app.dependency_overrides[get_llm_client] = lambda: llm

    response = client.put(
        f"/api/v1/bookmarks/{bookmark_id}/content",
        json={"content": "先保存原文，稍后再生成摘要", "generate_summary": False},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "success"
    assert data["summary"] is None
    assert data["content"] == "先保存原文，稍后再生成摘要"
    assert llm.calls == []


def test_manual_content_keeps_text_when_ai_output_is_invalid(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    bookmark_id = create(client, headers)
    llm = FakeLLMClient([result("bad"), result('{"summary":"缺少标签类型","tags":"wrong"}')])
    app.dependency_overrides[get_llm_client] = lambda: llm
    response = client.put(
        f"/api/v1/bookmarks/{bookmark_id}/content",
        json={"content": "保留这段正文"},
        headers=headers,
    )
    assert response.status_code == 502
    assert response.json()["code"] == 50202
    data = client.get(f"/api/v1/bookmarks/{bookmark_id}", headers=headers).json()["data"]
    assert data["status"] == "failed"
    assert data["content"] == "保留这段正文"


def test_manual_content_requires_authentication_and_valid_body(client: TestClient) -> None:
    headers, _ = auth_headers(client)
    bookmark_id = create(client, headers)
    assert client.put(
        f"/api/v1/bookmarks/{bookmark_id}/content", json={"content": "正文"}
    ).status_code == 401
    assert client.put(
        f"/api/v1/bookmarks/{bookmark_id}/content", json={"content": "  "}, headers=headers
    ).status_code == 422
