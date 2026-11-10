"""校验待办／日程的路由规则真的写进了提示词和工具说明，且评测集覆盖这条边界。"""

import json
from pathlib import Path

from app.llm.schemas import TOOL_ARG_MODELS, TOOL_DEFINITIONS

BACKEND_DIR = Path(__file__).parents[1]
PROMPT_PATH = BACKEND_DIR / "app" / "llm" / "prompts" / "intent.txt"
CASES_PATH = BACKEND_DIR / "evals" / "cases.jsonl"


def test_intent_prompt_explains_todo_versus_event() -> None:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "区分待办与日程" in prompt
    assert "即使带明确时间也使用 create_todo" in prompt
    assert "create_event" in prompt
    assert "去踢球" in prompt and "约了牙医" in prompt
    # 规则版本要能看出改动过，便于回溯线上实际使用的提示词。
    assert "版本：1.1.0" in prompt


def test_tool_descriptions_tell_model_where_scheduled_tasks_go() -> None:
    descriptions = {
        item["function"]["name"]: item["function"]["description"]  # type: ignore[index]
        for item in TOOL_DEFINITIONS
    }
    assert set(descriptions) == set(TOOL_ARG_MODELS)

    todo = descriptions["create_todo"]
    event = descriptions["create_event"]
    assert "待办" in todo and "due_at" in todo
    assert "不会出现在待办清单" in event
    # 不能再退回“只写工具名”的占位说明，否则模型只能靠猜。
    for name, text in descriptions.items():
        assert len(text) > 20, name


def test_eval_cases_cover_timed_task_routing() -> None:
    cases = [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line]

    by_text = {case["text"]: case["expect"] for case in cases}
    assert by_text["明天下午三点去踢球"]["tool"] == "create_todo"
    assert by_text["明天下午三点去踢球"]["args"]["due_at"] == "2026-10-31T15:00:00+08:00"
    assert by_text["周日下午四点在滨江公园跑步"]["tool"] == "create_todo"
    assert by_text["下周三下午两点半带猫去打疫苗"]["tool"] == "create_event"
    assert by_text["明天下午三点约了牙医"]["tool"] == "create_event"
