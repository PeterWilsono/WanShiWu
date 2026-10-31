"""手动真实模型评测；不会进入 pytest/CI，必须显式传 --confirm-real-api。"""

import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.assistant.service import parse_text  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.llm.client import LLMClient  # noqa: E402
from app.llm.models import LLMCallLog  # noqa: E402
from app.modules.auth.models import User  # noqa: E402

FIXED_NOW = datetime.fromisoformat("2026-10-30T09:00:00+08:00")


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        if not isinstance(case.get("id"), int) or not case.get("text") or not case.get("expect"):
            raise ValueError(f"评测用例第 {line_number} 行缺少 id/text/expect")
        cases.append(case)
    return cases


def expected_actions(case: dict[str, Any]) -> list[dict[str, Any]]:
    expect = case["expect"]
    return expect.get("actions", [expect])


def _equal_value(key: str, expected: Any, actual: Any) -> bool:
    if key == "title" and isinstance(expected, str) and isinstance(actual, str):
        expected_text = expected.strip().lower()
        actual_text = actual.strip().lower()
        return expected_text in actual_text or actual_text in expected_text
    if key in {"amount", "budget", "quantity"}:
        try:
            return Decimal(str(expected)) == Decimal(str(actual))
        except (InvalidOperation, ValueError):
            return False
    if key.endswith("_at") and isinstance(expected, str) and isinstance(actual, str):
        try:
            return datetime.fromisoformat(expected) == datetime.fromisoformat(actual)
        except ValueError:
            return False
    return expected == actual


def compare_actions(expected: list[dict[str, Any]], actual: list[dict[str, Any]]) -> dict[str, Any]:
    expected_tools = [item["tool"] for item in expected]
    actual_tools = [item["tool"] for item in actual]
    field_total = 0
    field_matched = 0
    field_errors: list[str] = []
    for index, expected_action in enumerate(expected):
        actual_action = actual[index] if index < len(actual) else {}
        actual_args = actual_action.get("args", {})
        for key, expected_value in expected_action.get("args", {}).items():
            field_total += 1
            if key in actual_args and _equal_value(key, expected_value, actual_args[key]):
                field_matched += 1
            else:
                field_errors.append(
                    f"action[{index}].{key}: expected={expected_value!r}, "
                    f"actual={actual_args.get(key)!r}"
                )
    return {
        "intent_correct": expected_tools == actual_tools,
        "expected_tools": expected_tools,
        "actual_tools": actual_tools,
        "field_total": field_total,
        "field_matched": field_matched,
        "field_errors": field_errors,
    }


def _last_log_id(db: Session) -> int:
    return db.scalar(select(func.coalesce(func.max(LLMCallLog.id), 0))) or 0


def _case_usage(db: Session, previous_log_id: int) -> dict[str, int]:
    logs = db.scalars(select(LLMCallLog).where(LLMCallLog.id > previous_log_id)).all()
    return {
        "prompt_tokens": sum(log.prompt_tokens for log in logs),
        "completion_tokens": sum(log.completion_tokens for log in logs),
        "latency_ms": sum(log.latency_ms for log in logs),
    }


def run(cases_path: Path) -> dict[str, Any]:
    # 独立内存库只保存评测日志与 pending 记录，不触碰开发数据库、不 confirm 业务动作。
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    results: list[dict[str, Any]] = []
    with Session(engine) as db:
        user = User(username="intent-eval", password_hash="not-used", timezone="Asia/Shanghai")
        db.add(user)
        db.commit()
        db.refresh(user)
        for case in load_cases(cases_path):
            previous_log_id = _last_log_id(db)
            actual: list[dict[str, Any]] = []
            error: str | None = None
            try:
                response = parse_text(
                    db,
                    user,
                    LLMClient(db, user.id),
                    case["text"],
                    current_time=FIXED_NOW,
                )
                if response.clarification:
                    actual = [
                        {
                            "tool": "ask_clarification",
                            "args": {"question": response.clarification},
                        }
                    ]
                else:
                    actual = [action.model_dump(mode="json") for action in response.actions]
            except AppError as exc:
                error = f"{exc.code}: {exc.message}"
            comparison = compare_actions(expected_actions(case), actual)
            results.append(
                {
                    "id": case["id"],
                    "text": case["text"],
                    **comparison,
                    "error": error,
                    **_case_usage(db, previous_log_id),
                }
            )
    case_count = len(results)
    expected_clarifications = sum(
        item["expected_tools"] == ["ask_clarification"] for item in results
    )
    clarification_recalled = sum(
        item["expected_tools"] == ["ask_clarification"]
        and item["actual_tools"] == ["ask_clarification"]
        for item in results
    )
    field_total = sum(item["field_total"] for item in results)
    return {
        "config": {
            "model": settings.llm_model,
            "fixed_now": FIXED_NOW.isoformat(),
            "timezone": "Asia/Shanghai",
            "cases": str(cases_path),
        },
        "metrics": {
            "case_count": case_count,
            "intent_accuracy": sum(item["intent_correct"] for item in results) / case_count,
            "field_accuracy": sum(item["field_matched"] for item in results) / field_total,
            "clarification_recall": clarification_recalled / expected_clarifications,
            "average_latency_ms": round(
                sum(item["latency_ms"] for item in results) / case_count, 2
            ),
            "prompt_tokens": sum(item["prompt_tokens"] for item in results),
            "completion_tokens": sum(item["completion_tokens"] for item in results),
            "total_tokens": sum(
                item["prompt_tokens"] + item["completion_tokens"] for item in results
            ),
            "failed_cases": sum(item["error"] is not None for item in results),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="万事屋 AI 意图真实模型评测（不在 CI 运行）")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.jsonl"))
    parser.add_argument("--output", type=Path, help="可选：把完整 JSON 结果写入该路径")
    parser.add_argument(
        "--confirm-real-api",
        action="store_true",
        help="明确允许访问已配置的模型服务并消耗额度",
    )
    args = parser.parse_args()
    if not args.confirm_real_api:
        parser.error("真实评测可能产生费用；确认后请显式添加 --confirm-real-api")
    if not settings.llm_api_key or settings.llm_api_key == "your-api-key-here":
        parser.error("请先在环境变量或 backend/.env 配置真实 LLM_API_KEY")
    report = run(args.cases)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
