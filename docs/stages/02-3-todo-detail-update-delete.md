# 阶段 2.3：待办详情、PATCH 修改与软删除

## 这一步在做什么

阶段 2.2 已经可以新建待办和查看列表，但还不能打开一条待办、修改它或删除它。本阶段补齐三个接口：

| 接口 | 作用 |
| --- | --- |
| `GET /api/v1/todos/{todo_id}` | 查看当前用户的一条有效待办 |
| `PATCH /api/v1/todos/{todo_id}` | 只修改请求里明确给出的字段 |
| `DELETE /api/v1/todos/{todo_id}` | 软删除待办，列表和详情不再返回它 |

这三个接口与前面的新建、列表组合起来，就是常见的 CRUD：创建（Create）、读取（Read）、更新（Update）、删除（Delete）。

## 需要理解的知识

### 1. 为什么修改使用 PATCH，而不是 PUT

- **PUT** 通常表示用请求内容替换整个资源，调用方需要提供完整对象。
- **PATCH** 表示局部修改，例如只传 `{ "priority": 3 }`，其他字段保持原样。

待办有标题、备注、截止时间、优先级、状态等多个字段。编辑优先级时不应该要求前端把所有旧值重新提交，因此这里选择 PATCH。

### 2. “没有传”和“传了 null”不是一回事

例如：

```json
{ "note": null }
```

表示清空备注；而：

```json
{ "priority": 3 }
```

表示只改优先级，备注不动。

Pydantic 会记录请求中实际出现了哪些字段。service 使用：

```python
data.model_dump(exclude_unset=True)
```

只导出明确提交的字段。若直接使用普通 `model_dump()`，所有未提交字段也会以默认值 `None` 出现，可能把原有数据意外清空。

标题、优先级、状态、周期和标签不允许为 `null`；备注和截止时间允许显式清空；标签使用空数组 `[]` 清空。

### 3. 为什么完成时间由后端维护

当状态改为 `done` 时，后端通过统一的 `now_utc()` 写入 `completed_at`；改为 `pending` 或 `cancelled` 时清空完成时间。

客户端不能直接提交 `completed_at`，这样可避免“状态还是待完成，却已经有完成时间”之类的不一致数据，也方便以后统一测试时间相关逻辑。

### 4. 什么是软删除

删除接口没有执行 SQL `DELETE`，而是：

```python
todo.deleted_at = now_utc()
```

原记录仍在数据库中，但所有正常查询都带有 `deleted_at IS NULL`，所以用户看不到它。

这样做的好处是保留历史痕迹，未来可以实现回收站、误删恢复或审计。代价是每张业务表的每个查询都不能忘记软删除过滤，因此项目把这项规则作为数据层的强制约定。

### 5. 为什么越权和不存在都返回 404

查询单条待办时同时限定：

- `id` 必须匹配；
- `user_id` 必须是当前登录用户；
- `deleted_at` 必须为空。

其他用户的待办、已经删除的待办和从未存在的待办，都返回 HTTP 404、业务码 40401。这样不会向调用方泄露“某个 ID 的数据其实存在，只是属于别人”。

## 代码如何配合

- `life/schemas.py`：新增 `TodoUpdate`，定义可修改字段和校验规则。
- `life/service.py`：新增 `get_todo`、`update_todo`、`delete_todo`；读取、修改、删除共用同一个带用户隔离和软删除过滤的查询入口。
- `life/router.py`：注册详情、PATCH、DELETE 路由，并继续使用统一响应格式。
- `tests/test_life_todos_api.py`：补充成功、参数非法、未登录、越权、软删除和回归场景。

调用顺序是：路由接收请求 → 登录依赖确认用户 → Pydantic 校验输入 → service 查询并修改数据库 → 路由返回统一 JSON。

## 调用示例

局部修改标题和优先级：

```bash
curl -X PATCH http://localhost:8000/api/v1/todos/1 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"新标题","priority":3}'
```

清空截止时间：

```json
{ "due_at": null }
```

软删除：

```bash
curl -X DELETE http://localhost:8000/api/v1/todos/1 \
  -H "Authorization: Bearer <token>"
```

成功响应为：

```json
{ "code": 0, "message": "删除成功", "data": null }
```

## 如何验证

在 `backend/` 下运行：

```bash
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -v
```

本阶段验证结果：Ruff 全部通过，完整后端回归 **62 项测试全部通过**。测试还直接读取数据库确认：软删除后记录仍存在、`deleted_at` 已写入，而列表、详情及重复删除都无法再访问该记录。

## 下一步

阶段 2.4 将实现专用的“完成待办”接口，以及周期性待办：完成一个每日、每周或每月待办时，在同一事务中创建下一次待办。
