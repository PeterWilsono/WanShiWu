"""注册、登录和 JWT 鉴权接口测试（正常流程 / 参数错误 / 未登录 / 业务冲突）。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.modules.auth.models import User

PASSWORD = "correct-horse-123"


def register(client: TestClient, username: str = "peter"):
    return client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})


def login(client: TestClient, username: str = "peter", password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_register_login_and_me(client: TestClient, db_session: Session) -> None:
    response = register(client)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["username"] == "peter"
    assert "password" not in body["data"]
    assert "password_hash" not in body["data"]

    user = db_session.scalar(select(User).where(User.username == "peter"))
    assert user is not None
    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)

    response = login(client)
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    assert response.json()["data"]["token_type"] == "bearer"

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["data"]["id"] == user.id
    assert response.json()["data"]["username"] == "peter"


def test_register_duplicate_username_returns_conflict(client: TestClient) -> None:
    assert register(client).status_code == 200
    response = register(client)
    assert response.status_code == 409
    assert response.json()["code"] == 40901
    assert response.json()["message"] == "用户名已存在"


def test_register_validation_error(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={"username": "a", "password": "short"})
    assert response.status_code == 422
    assert response.json()["code"] == 40001
    assert response.json()["data"]["errors"]


@pytest.mark.parametrize("username", ["peter", "unknown"])
def test_login_bad_credentials_use_same_error(client: TestClient, username: str) -> None:
    register(client)
    response = login(client, username=username, password="wrong-password")
    assert response.status_code == 401
    assert response.json()["code"] == 40102
    assert response.json()["message"] == "用户名或密码错误"


def test_me_without_token_returns_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_me_with_invalid_token_returns_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_me_with_expired_token_returns_unauthorized(client: TestClient) -> None:
    user_id = register(client).json()["data"]["id"]
    token = create_access_token(user_id, expires_minutes=-1)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_me_with_token_for_missing_user_returns_unauthorized(client: TestClient) -> None:
    token = create_access_token(999999)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_register_can_be_disabled(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "allow_register", False)
    response = register(client)
    assert response.status_code == 404
    assert response.json()["code"] == 40401
