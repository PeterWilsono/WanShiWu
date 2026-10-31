# 阶段 3.2：统一 LLM 客户端、调用日志与每日限额

## 这一步做什么

建立项目唯一的大模型调用入口 `app/llm/client.py`，并新增 `llm_call_logs` 表。后续 AI 入口、菜谱、摘要、行程都必须经过这个客户端，不能在业务模块里直接调用 OpenAI SDK。

本任务没有真实请求模型服务，所有测试都使用模拟 SDK。

## 统一接口

```python
chat(messages, tools=None, response_format=None, module=..., purpose=...) -> LLMResult
```

`LLMResult` 包含文本、工具调用、Prompt tokens、Completion tokens 和耗时。工具调用的 arguments 必须是合法 JSON 对象，否则写入 `invalid_output` 失败日志并抛出 50202；具体业务字段是否合法由后续 Pydantic 工具模型继续校验。

## 超时与重试

SDK 从环境配置读取 base_url、api_key、model 和 timeout，默认 30 秒。SDK 自己的重试被关闭（`max_retries=0`），避免两套重试叠加。

统一客户端最多执行 3 次请求：首次 + 2 次重试。

- 网络连接错误、超时：可重试。
- HTTP 5xx：可重试。
- HTTP 4xx：不重试。
- 退避间隔：0.5 秒、1 秒，测试中注入假 sleep，不会真的等待。
- 最终仍失败：写失败日志，向业务层抛出 50201，不暴露 SDK 堆栈、密钥或服务商原始错误。

## 调用日志与隐私

`llm_call_logs` 保存：用户、模块、用途、模型、token 用量、耗时、success、error_type、时间。

**没有 Prompt 和响应全文字段**，避免把账目、日程等隐私写入审计日志。一次 `chat()` 是“一条逻辑调用”，中间重试不各写一条；最终成功或失败写一条记录。

日志使用客户端注入的当前时间，保证测试可复现，并与限额检查使用同一时间基准。token 和 latency 在数据库中有非负约束，常用查询有 `(user_id, created_at)` 索引。

## 每日限额

调用前先统计当前用户、当地自然日内已有的调用日志；成功和失败都占额度。达到 `DAILY_LLM_CALL_LIMIT` 时不再请求 SDK，抛出 HTTP 429 / 42901。

这里不能直接用 UTC 日期：上海时间凌晨的“今天”与 UTC 的“今天”不同。实现先按 users.timezone 求当地 00:00，再转换成左闭右开的 UTC 区间。

## 改动文件

- `backend/app/llm/client.py`：统一客户端、结果模型、重试、限额、日志。
- `backend/app/llm/models.py`：llm_call_logs 模型与约束。
- `backend/alembic/versions/1d9446591c62_create_llm_call_logs_table.py`：数据库迁移。
- `backend/tests/test_llm_client.py`：6 个专项测试（含网络/5xx 参数化场景）。
- Alembic env 和测试 conftest：注册新模型。

## 验证结果

- LLM 专项 6 项通过。
- 完整后端回归 **219 项全部通过**。
- Ruff 检查与格式检查通过。
- 开发数据库已执行迁移至 `1d9446591c62`。

## 当前边界

限额适合当前单用户、单后端进程场景，未引入 Redis 或分布式计数。日志与业务共用请求数据库会话，因此调用 LLM 时应放在业务写入之前；后续 parse 正是先解析、后创建待确认记录。真实模型连通性和额度需用户配置密钥后手动验收。
