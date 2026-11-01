"""从模型文本中安全提取 JSON 对象，兼容代码围栏和简短前后说明。"""

import json
import re
from typing import Any

_THINK_BLOCK = re.compile(r"<think>.*?</think>", flags=re.IGNORECASE | re.DOTALL)
_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", flags=re.IGNORECASE | re.DOTALL)


def parse_json_object(text: str) -> dict[str, Any]:
    """只返回 JSON 对象；数组、标量和无法解析的文本仍明确报错。"""
    cleaned = _THINK_BLOCK.sub("", text).strip()
    candidates = [cleaned, *(match.group(1).strip() for match in _JSON_FENCE.finditer(cleaned))]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(value, dict):
                return value

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        try:
            value, _ = decoder.raw_decode(cleaned[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise json.JSONDecodeError("模型响应中没有完整 JSON 对象", text, 0)
