"""测试用 LLM 客户端：按队列返回预设结果，绝不访问网络。"""

from collections import deque
from collections.abc import Iterable

from app.llm.client import LLMResult


class FakeLLMClient:
    """与 LLMClient.chat 保持同签名，并记录每次 Prompt 供断言。"""

    def __init__(self, results: Iterable[LLMResult | Exception] = ()) -> None:
        self.results = deque(results)
        self.calls: list[dict[str, object]] = []

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]] | None = None,
        response_format: dict[str, object] | None = None,
        *,
        module: str,
        purpose: str,
    ) -> LLMResult:
        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
                "response_format": response_format,
                "module": module,
                "purpose": purpose,
            }
        )
        if not self.results:
            raise AssertionError("FakeLLMClient 没有可用的预设结果")
        result = self.results.popleft()
        if isinstance(result, Exception):
            raise result
        return result
