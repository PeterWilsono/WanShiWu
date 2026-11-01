"""AI 菜谱结构校验、重试、库存重核算与用户隔离测试。"""

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.assistant.dependencies import get_llm_client
from app.llm.client import LLMResult
from app.llm.fake import FakeLLMClient
from app.main import app

PASSWORD = "correct-recipe-output-521"
NOW = datetime(2026, 11, 1, 1, 0, tzinfo=UTC)


def auth_headers(client: TestClient, username: str = "recipe-ai") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"username": username, "password": PASSWORD})
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_ingredient(
    client: TestClient,
    headers: dict[str, str],
    name: str,
    quantity: str,
    unit: str,
    expire_on: str | None = None,
) -> None:
    response = client.post(
        "/api/v1/ingredients",
        headers=headers,
        json={
            "name": name,
            "quantity": quantity,
            "unit": unit,
            "storage": "fridge",
            "expire_on": expire_on,
        },
    )
    assert response.status_code == 200, response.text


def llm_result(payload: object) -> LLMResult:
    return LLMResult(
        text=payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False),
        tool_calls=[],
        prompt_tokens=20,
        completion_tokens=30,
        latency_ms=50,
    )


def recipe_payload() -> dict:
    return {
        "recipes": [
            {
                "name": "番茄炒蛋",
                "minutes": 20,
                "uses": [{"name": "鸡蛋", "quantity": "3", "unit": "个"}],
                "missing": [],
                "steps": ["鸡蛋打散，番茄切块。", "分别炒熟后混合调味。"],
            },
            {
                "name": "清炒菠菜",
                "minutes": 10,
                "uses": [{"name": "菠菜", "quantity": "200", "unit": "克"}],
                "missing": [],
                "steps": ["菠菜洗净沥干。", "热锅快炒并调味。"],
            },
            {
                "name": "番茄汤",
                "minutes": 15,
                "uses": [{"name": "番茄", "quantity": "50", "unit": "克"}],
                "missing": [{"name": "番茄", "quantity": "100", "unit": "克"}],
                "steps": ["番茄切块。", "加水煮开并调味。"],
            },
        ]
    }


def use_fake(fake: FakeLLMClient) -> None:
    app.dependency_overrides[get_llm_client] = lambda: fake


def recommend(client: TestClient, headers: dict[str, str], **payload: object):
    return client.post("/api/v1/pantry/recipes", headers=headers, json=payload)


def test_recipe_prompt_and_stock_reconciliation_use_only_current_user(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.modules.pantry.recipe_service.now_utc", lambda: NOW)
    headers = auth_headers(client)
    other_headers = auth_headers(client, "recipe-other")
    create_ingredient(client, headers, "鸡蛋", "2", "个", "2026-11-03")
    create_ingredient(client, headers, "番茄", "100", "克", "2026-11-02")
    create_ingredient(client, other_headers, "鸡蛋", "10", "个")
    create_ingredient(client, other_headers, "秘密食材", "1", "包")
    fake = FakeLLMClient([llm_result(recipe_payload())])
    use_fake(fake)

    response = recommend(client, headers, preferences=" 清淡，少油 ", servings=3)

    assert response.status_code == 200, response.text
    recipes = response.json()["data"]["recipes"]
    assert len(recipes) == 3
    assert recipes[0]["uses"] == [{"name": "鸡蛋", "quantity": "2.00", "unit": "个"}]
    assert recipes[0]["missing"] == [{"name": "鸡蛋", "quantity": "1.00", "unit": "个"}]
    assert recipes[1]["uses"] == []
    assert recipes[1]["missing"][0]["quantity"] == "200.00"
    assert recipes[2]["uses"][0]["quantity"] == "100.00"
    assert recipes[2]["missing"][0]["quantity"] == "50.00"

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    assert call["module"] == "pantry" and call["purpose"] == "recipe"
    user_data = json.loads(call["messages"][1]["content"])
    assert user_data["today"] == "2026-11-01"
    assert user_data["servings"] == 3 and user_data["preferences"] == "清淡，少油"
    assert [item["name"] for item in user_data["inventory"]] == ["番茄", "鸡蛋"]
    assert "秘密食材" not in call["messages"][1]["content"]


def test_recipe_accepts_fenced_verbose_output_and_ignores_extra_metadata(
    client: TestClient,
) -> None:
    headers = auth_headers(client)
    payload = {
        **recipe_payload(),
        "summary": "模型附带的说明，不参与业务",
        "recipes": [
            {
                **recipe,
                "minutes": str(recipe["minutes"]),
                "difficulty": "简单",
                "uses": [{**item, "note": "附带说明"} for item in recipe["uses"]],
            }
            for recipe in recipe_payload()["recipes"]
        ],
    }
    serialized = json.dumps(payload, ensure_ascii=False)
    text = f"<think>先考虑清淡少油</think>以下是菜谱：\n```json\n{serialized}\n```"
    fake = FakeLLMClient([llm_result(text)])
    use_fake(fake)

    response = recommend(client, headers, preferences="清淡少油")

    assert response.status_code == 200, response.text
    assert len(response.json()["data"]["recipes"]) == 3
    assert "difficulty" not in response.json()["data"]["recipes"][0]
    assert len(fake.calls) == 1


def test_recipe_invalid_output_retries_once_then_accepts_valid_json(client: TestClient) -> None:
    headers = auth_headers(client)
    fake = FakeLLMClient([llm_result("不是 JSON"), llm_result(recipe_payload())])
    use_fake(fake)

    response = recommend(client, headers)

    assert response.status_code == 200, response.text
    assert len(response.json()["data"]["recipes"]) == 3
    assert len(fake.calls) == 2
    assert "未通过菜谱 JSON 校验" in fake.calls[1]["messages"][-1]["content"]


@pytest.mark.parametrize(
    "payload",
    [
        "```json\n{}\n```",
        [],
        {"recipes": []},
        {
            "recipes": [
                {
                    **recipe_payload()["recipes"][0],
                    "uses": [{"name": "鸡蛋", "quantity": "0", "unit": "个"}],
                },
                *recipe_payload()["recipes"][1:],
            ]
        },
        {
            "recipes": [
                {
                    **recipe_payload()["recipes"][0],
                    "uses": [{"name": "鸡蛋", "quantity": "1", "unit": "箱"}],
                },
                *recipe_payload()["recipes"][1:],
            ]
        },
    ],
)
def test_recipe_rejects_invalid_structure_after_one_retry(
    client: TestClient, payload: object
) -> None:
    headers = auth_headers(client)
    fake = FakeLLMClient([llm_result(payload), llm_result(payload)])
    use_fake(fake)

    response = recommend(client, headers)

    assert response.status_code == 502 and response.json()["code"] == 50202
    assert len(fake.calls) == 2


def test_recipe_request_validation_and_authentication(client: TestClient) -> None:
    headers = auth_headers(client)
    fake = FakeLLMClient([llm_result(recipe_payload())])
    use_fake(fake)

    invalid = recommend(client, headers, servings=13)
    unauthenticated = client.post("/api/v1/pantry/recipes", json={})

    assert invalid.status_code == 422 and invalid.json()["code"] == 40001
    assert unauthenticated.status_code == 401
    assert len(fake.calls) == 0
