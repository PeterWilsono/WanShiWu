"""AI confirm 流程：二次校验、dispatch、幂等、隔离与原子事务。"""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assistant.models import AssistantRecord, AssistantStatus
from app.modules.inbox.models import Bookmark
from app.modules.life.models import Event, Reminder, Todo, Transaction
from app.modules.pantry.models import Ingredient

PASSWORD = "correct-horse-123"


def auth_headers(client: TestClient, username: str = "confirm-user") -> tuple[dict[str, str], dict]:
    user = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    ).json()["data"]
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def pending_record(db: Session, user_id: int, actions: list[dict]) -> AssistantRecord:
    record = AssistantRecord(
        user_id=user_id,
        raw_text="测试确认",
        intent=actions[0]["tool"] if len(actions) == 1 else "multi_action",
        parsed_json=[{**action, "summary": "候选动作"} for action in actions],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def confirm(client: TestClient, headers: dict[str, str], record_id: int, actions: list[dict]):
    return client.post(
        "/api/v1/assistant/confirm",
        headers=headers,
        json={
            "record_id": record_id,
            "actions": [{**action, "summary": "用户已核对"} for action in actions],
        },
    )


def test_confirm_todo_allows_user_edits_and_marks_executed(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    record = pending_record(
        db_session, user["id"], [{"tool": "create_todo", "args": {"title": "旧标题"}}]
    )

    response = confirm(
        client,
        headers,
        record.id,
        [
            {
                "tool": "create_todo",
                "args": {
                    "title": " 用户修改后的待办 ",
                    "due_at": "2026-11-06T23:59:00+08:00",
                    "priority": 3,
                    "note": "确认卡片修改",
                },
            }
        ],
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "executed"
    assert data["results"] == [{"tool": "create_todo", "ref": "todo:1", "id": 1}]
    todo = db_session.execute(select(Todo)).scalar_one()
    assert todo.title == "用户修改后的待办"
    assert todo.priority == 3 and todo.due_at is not None
    db_session.refresh(record)
    assert record.status == AssistantStatus.EXECUTED
    assert record.result_ref == f"todo:{todo.id}"
    assert record.executed_at is not None and record.error is None
    assert record.parsed_json[0]["args"]["title"] == "用户修改后的待办"
    assert record.parsed_json[0]["summary"] == "新建待办：用户修改后的待办"


def test_confirm_expense_converts_decimal_yuan_to_cents(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    record = pending_record(
        db_session,
        user["id"],
        [{"tool": "add_expense", "args": {"amount": "35.55", "category": "餐饮"}}],
    )

    response = confirm(
        client,
        headers,
        record.id,
        [
            {
                "tool": "add_expense",
                "args": {
                    "amount": 35.55,
                    "category": "餐饮",
                    "note": "午饭",
                    "occurred_at": "2026-10-31T12:00:00+08:00",
                },
            }
        ],
    )

    assert response.status_code == 200, response.text
    transaction = db_session.execute(select(Transaction)).scalar_one()
    assert transaction.amount_cents == 3555
    assert transaction.type == "expense" and transaction.source == "assistant"
    assert transaction.category.name == "餐饮"
    assert response.json()["data"]["results"][0]["ref"] == f"transaction:{transaction.id}"


def test_confirm_event_also_creates_reminder_in_same_transaction(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    args = {
        "title": "牙医",
        "start_at": "2026-10-31T15:00:00+08:00",
        "remind_before_min": 30,
    }
    record = pending_record(db_session, user["id"], [{"tool": "create_event", "args": args}])

    response = confirm(client, headers, record.id, [{"tool": "create_event", "args": args}])

    assert response.status_code == 200, response.text
    event = db_session.execute(select(Event)).scalar_one()
    reminder = db_session.execute(select(Reminder)).scalar_one()
    assert reminder.target_id == event.id and reminder.deleted_at is None
    assert reminder.remind_at.isoformat() == "2026-10-31T06:30:00+00:00"


def test_confirm_multiple_actions_commits_all_results_together(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    actions = [
        {"tool": "create_todo", "args": {"title": "采购后报销"}},
        {"tool": "add_expense", "args": {"amount": 80, "category": "购物"}},
    ]
    record = pending_record(db_session, user["id"], actions)

    response = confirm(client, headers, record.id, actions)

    assert response.status_code == 200, response.text
    results = response.json()["data"]["results"]
    assert [item["tool"] for item in results] == ["create_todo", "add_expense"]
    assert db_session.scalar(select(func.count()).select_from(Todo)) == 1
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 1
    db_session.refresh(record)
    assert record.result_ref == f"{results[0]['ref']},{results[1]['ref']}"


def test_confirm_multiple_actions_rolls_back_all_when_one_fails(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    actions = [
        {"tool": "create_todo", "args": {"title": "不能单独留下"}},
        {"tool": "add_expense", "args": {"amount": 20, "category": "不存在的分类"}},
    ]
    record = pending_record(db_session, user["id"], actions)

    response = confirm(client, headers, record.id, actions)

    assert response.status_code == 422
    assert response.json()["code"] == 42201
    assert db_session.scalar(select(func.count()).select_from(Todo)) == 0
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 0
    db_session.refresh(record)
    assert record.status == AssistantStatus.FAILED
    assert record.result_ref is None and record.executed_at is None


def test_confirm_ingredient_allows_user_edits_and_creates_batch(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    original = {"name": "鸡蛋", "quantity": 2, "unit": "个"}
    record = pending_record(
        db_session, user["id"], [{"tool": "add_ingredient", "args": original}]
    )
    edited = {
        "name": " 可生食鸡蛋 ",
        "quantity": "6.50",
        "unit": "个",
        "expire_on": "2026-11-08",
        "storage": "fridge",
    }

    response = confirm(
        client, headers, record.id, [{"tool": "add_ingredient", "args": edited}]
    )

    assert response.status_code == 200, response.text
    ingredient = db_session.execute(select(Ingredient)).scalar_one()
    assert ingredient.name == "可生食鸡蛋"
    assert str(ingredient.quantity) == "6.50"
    assert ingredient.expire_on.isoformat() == "2026-11-08"
    assert ingredient.storage == "fridge"
    assert response.json()["data"]["results"] == [
        {"tool": "add_ingredient", "ref": f"ingredient:{ingredient.id}", "id": ingredient.id}
    ]


def test_confirm_ingredient_rolls_back_when_later_action_fails(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    actions = [
        {"tool": "add_ingredient", "args": {"name": "鸡蛋", "quantity": 6, "unit": "个"}},
        {"tool": "add_expense", "args": {"amount": 20, "category": "不存在的分类"}},
    ]
    record = pending_record(db_session, user["id"], actions)

    response = confirm(client, headers, record.id, actions)

    assert response.status_code == 422 and response.json()["code"] == 42201
    assert db_session.scalar(select(func.count()).select_from(Ingredient)) == 0
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 0


def test_confirm_is_idempotent_and_repeated_request_returns_conflict(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    actions = [{"tool": "create_todo", "args": {"title": "只能创建一次"}}]
    record = pending_record(db_session, user["id"], actions)

    first = confirm(client, headers, record.id, actions)
    second = confirm(client, headers, record.id, actions)

    assert first.status_code == 200
    assert second.status_code == 409 and second.json()["code"] == 40901
    assert db_session.scalar(select(func.count()).select_from(Todo)) == 1


def test_confirm_other_users_record_returns_404_without_execution(
    client: TestClient, db_session: Session
) -> None:
    _, owner = auth_headers(client, "owner")
    actions = [{"tool": "create_todo", "args": {"title": "他人记录"}}]
    record = pending_record(db_session, owner["id"], actions)
    headers, _ = auth_headers(client, "other-user")

    response = confirm(client, headers, record.id, actions)

    assert response.status_code == 404 and response.json()["code"] == 40401
    assert db_session.scalar(select(func.count()).select_from(Todo)) == 0
    db_session.refresh(record)
    assert record.status == AssistantStatus.PENDING


def test_confirm_save_bookmark_creates_pending_record(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    actions = [{
        "tool": "save_bookmark",
        "args": {"url": "https://example.com/read", "note": "稍后阅读"},
    }]
    record = pending_record(db_session, user["id"], actions)
    response = confirm(client, headers, record.id, actions)
    assert response.status_code == 200
    assert response.json()["data"]["results"][0]["ref"].startswith("bookmark:")
    bookmark = db_session.scalar(select(Bookmark).where(Bookmark.user_id == user["id"]))
    assert bookmark is not None
    assert bookmark.status == "pending"
    assert bookmark.note == "稍后阅读"


def test_confirm_rejects_invalid_or_unsupported_actions_and_marks_failed(
    client: TestClient, db_session: Session
) -> None:
    headers, user = auth_headers(client)
    invalid = pending_record(
        db_session,
        user["id"],
        [{"tool": "add_expense", "args": {"amount": 1, "category": "餐饮"}}],
    )
    invalid_response = confirm(
        client,
        headers,
        invalid.id,
        [{"tool": "add_expense", "args": {"amount": -1, "category": "餐饮"}}],
    )
    unsupported = pending_record(
        db_session,
        user["id"],
        [{"tool": "create_trip", "args": {"destination": "杭州", "days": 2}}],
    )
    unsupported_response = confirm(
        client,
        headers,
        unsupported.id,
        [{"tool": "create_trip", "args": {"destination": "杭州", "days": 2}}],
    )

    assert invalid_response.status_code == 422
    assert invalid_response.json()["code"] == 40001
    unauthenticated = client.post(
        "/api/v1/assistant/confirm",
        json={"record_id": invalid.id, "actions": []},
    )

    assert invalid_response.status_code == 422
    assert invalid_response.json()["code"] == 40001
    assert unsupported_response.status_code == 422
    assert "尚未开放" in unsupported_response.json()["message"]
    assert unauthenticated.status_code == 401
    db_session.refresh(invalid)
    db_session.refresh(unsupported)
    assert invalid.status == AssistantStatus.FAILED
    assert unsupported.status == AssistantStatus.FAILED
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 0
