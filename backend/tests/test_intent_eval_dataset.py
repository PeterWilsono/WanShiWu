"""离线校验评测数据与指标比较逻辑；绝不调用真实模型。"""

import sys
from pathlib import Path

from app.llm.schemas import TOOL_ARG_MODELS

BACKEND_DIR = Path(__file__).parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evals.run_intent_eval import compare_actions, expected_actions, load_cases  # noqa: E402

CASES_PATH = BACKEND_DIR / "evals" / "cases.jsonl"


def test_eval_dataset_covers_all_tools_and_has_enough_clarifications() -> None:
    cases = load_cases(CASES_PATH)

    assert len(cases) >= 30
    assert len({case["id"] for case in cases}) == len(cases)
    tools = {action["tool"] for case in cases for action in expected_actions(case)}
    assert tools == set(TOOL_ARG_MODELS)
    clarification_count = sum(
        expected_actions(case)[0]["tool"] == "ask_clarification" for case in cases
    )
    assert clarification_count >= 5
    for case in cases:
        for action in expected_actions(case):
            if action["tool"] == "ask_clarification":
                continue  # 只要求追问，不限定模型必须使用哪一句问题文本。
            # 期望字段可以是工具参数的子集，但字段名和值本身必须合法。
            TOOL_ARG_MODELS[action["tool"]].model_validate(action.get("args", {}))


def test_eval_comparison_handles_titles_exact_values_and_multiple_actions() -> None:
    expected = [
        {
            "tool": "create_todo",
            "args": {"title": "报销单", "due_at": "2026-11-04T23:59:00+08:00"},
        },
        {"tool": "add_expense", "args": {"amount": "35.50", "category": "餐饮"}},
    ]
    actual = [
        {
            "tool": "create_todo",
            "args": {"title": "把报销单交了", "due_at": "2026-11-04T15:59:00Z"},
        },
        {"tool": "add_expense", "args": {"amount": 35.5, "category": "餐饮"}},
    ]

    comparison = compare_actions(expected, actual)

    assert comparison["intent_correct"] is True
    assert comparison["field_total"] == 4
    assert comparison["field_matched"] == 4
    assert comparison["field_errors"] == []


def test_eval_comparison_reports_wrong_tool_and_missing_field() -> None:
    comparison = compare_actions(
        [{"tool": "add_expense", "args": {"amount": 35, "category": "餐饮"}}],
        [{"tool": "add_income", "args": {"amount": 35}}],
    )

    assert comparison["intent_correct"] is False
    assert comparison["field_matched"] == 1
    assert len(comparison["field_errors"]) == 1
    assert "category" in comparison["field_errors"][0]
