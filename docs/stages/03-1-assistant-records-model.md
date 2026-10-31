# 阶段 3.1：AI 助手记录模型与迁移

## 这一步做什么

建立 `assistant_records` 表，为后续“一句话录入”保存解析与确认记录。它记录 AI 提议了什么、用户是否确认、执行后产生了哪个对象、失败原因是什么。

本任务只做数据基础，不调用模型，也不开放 parse / confirm 接口。

## 为什么需要单独的表

AI 解析和业务写入是两步：

```text
用户原话 → AI 提议 → pending 等待确认 → 用户确认 → executed
                                  └→ 用户取消 → cancelled
                                  └→ 执行失败 → failed
```

如果只保存最终待办或账目，就无法回答“这条数据来自哪句话”“用户是否确认过”“重复确认会发生什么”。独立记录让流程可追踪，也为后续幂等校验提供依据。

## 字段职责

- `raw_text`：用户原始输入，数据库限制不能为空字符串。
- `intent`：主要工具名，或 clarification / unknown。
- `parsed_json`：经校验的候选动作列表，默认空数组；不是任意模型文本的直接执行脚本。
- `status`：pending / executed / cancelled / failed，使用字符串枚举和数据库约束。
- `result_ref`：执行成功后的对象引用，例如 `todo:12`。
- `error`：失败原因，正常待确认时为空。
- `executed_at`：实际执行时间，UTC 存储。

同时包含公共的 id、user_id、created_at、updated_at、deleted_at。查询时必须按用户隔离。

## 索引与测试

复合索引 `ix_assistant_records_user_status_created_at(user_id, status, created_at)` 服务于“查看当前用户的待确认记录/按时间查看历史”。

新增 `test_assistant_models.py` 4 项测试，覆盖：

1. 默认 pending、JSON 候选动作、UTC 时间和执行字段更新。
2. 复合索引字段顺序。
3. 空原始输入被数据库约束拒绝。
4. 非法状态被 SQLAlchemy 枚举校验提前拒绝。

非法状态在 ORM 写库前抛出 `StatementError`，空文本在数据库层抛出 `IntegrityError`；测试区分了两种防线，而不是强迫所有错误都来自数据库。

## 迁移与验证

- 新增迁移 `011e1f5c341c_create_assistant_records_table.py`，前一个版本为 reminders。
- Alembic env 与测试 conftest 都注册 assistant models，保证自动迁移和内存测试库包含新表。
- 真实开发数据库已执行 `upgrade head`。
- `alembic check` 返回 `No new upgrade operations detected`。
- 完整后端回归 **213 项全部通过**，Ruff 检查与格式检查通过。

## 下一步

实现统一 LLM Client 和 llm_call_logs，再让 parse 通过依赖注入调用真实或 Fake 客户端；测试过程中不会真实调用外部模型。
