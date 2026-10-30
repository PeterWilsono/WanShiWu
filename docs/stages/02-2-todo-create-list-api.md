# 阶段 2.2：待办 Schema、新建与列表 API

## 这一阶段在做什么

这一阶段把 2.1 的 todos 表变成真正可调用的后端功能：

- `POST /api/v1/todos`：登录用户新建待办。
- `GET /api/v1/todos`：查询自己的待办列表。
- 支持分页、排序，以及状态、截止时间范围、标签筛选。
- 参数错误返回统一的 40001，未登录返回 40101。
- 其他用户的待办和已软删除的待办不会出现在列表里。

请求链路为：

```text
HTTP JSON / 查询参数
  → Pydantic Schema 校验
  → Router 获取当前用户和数据库会话
  → Service 执行业务规则与查询
  → SQLAlchemy 读写 SQLite
  → 统一 code / message / data 响应
```

## 主要文件

- `backend/app/modules/life/schemas.py`：新建、列表查询、单条与列表响应 Schema。
- `backend/app/modules/life/service.py`：新建待办、列表过滤、分页排序。
- `backend/app/modules/life/router.py`：两个 HTTP 接口和响应序列化。
- `backend/app/main.py`：挂载生活管家路由。
- `backend/app/core/errors.py`：修复自定义校验错误的 JSON 序列化。
- `backend/tests/test_life_todos_api.py`：15 个待办接口测试场景。

## 用到的主要知识

### 1. Schema、Model、Service、Router 各自负责什么

- Model：数据库表怎么存，例如字段叫 `tags_json`。
- Schema：接口允许接收和返回什么，例如对外叫更自然的 `tags`。
- Service：业务规则、查询条件和事务。
- Router：HTTP 参数、当前用户依赖、调用 service、组装响应。

数据库内部字段和 API 字段不必永远一模一样。`TodoResponse` 用 `validation_alias="tags_json"` 从模型读取，再输出为 `tags`，避免把数据库命名细节泄漏给前端。

### 2. 新建待办时哪些字段由服务端决定

用户提交标题、备注、截止时间、优先级、周期和标签。`status` 默认由模型设为 pending，`completed_at` 为空，`user_id` 来自 JWT 对应的当前用户，而不是请求 JSON。

不能让客户端随意提交 `user_id`，否则可能把数据写到别人名下。用户身份必须来自经过验证的 Token。

### 3. 时间为什么必须带时区

`2026-10-31T15:00:00` 没有说明是北京时间还是 UTC，直接保存会产生歧义。因此接口要求 ISO 8601 时间带偏移，例如：

```text
2026-10-31T15:00:00+08:00
```

Schema 把它转换为 UTC 后交给数据库。测试验证这个北京时间会保存并返回为对应的 `2026-10-31 07:00 UTC`。

### 4. 标签清理与精确筛选

新建时会：

- 去除标签首尾空白；
- 拒绝空白标签；
- 按原顺序去重。

列表按标签筛选时，不能简单使用 `LIKE '%工作%'`，否则「工作」会误匹配「远程工作」。本阶段使用 SQLite `json_each` 展开 JSON 数组，再用绑定参数精确比较某个元素。

绑定参数由数据库驱动处理，不能把用户输入直接拼进 SQL 字符串，因此同时具备准确性和 SQL 注入防护。

### 5. 分页为什么同时需要 items 和 total

`items` 是当前页数据，`total` 是所有符合筛选条件的条数。前端需要 total 计算总页数，例如 95 条、每页 20 条就是 5 页。

实现中 total 使用独立 `COUNT` 查询，列表查询再使用：

```text
offset = (page - 1) * page_size
limit = page_size
```

`page` 从 1 开始，`page_size` 最大 100，避免一次请求无限制读取数据。

### 6. 排序为什么要加 id 作为第二排序键

两条待办可能有相同创建时间或优先级。如果只按这些字段排序，数据库在不同页面查询中的相对顺序可能不稳定，造成同一条记录重复出现或漏掉。

本阶段在用户选择的排序字段后再按 id 同方向排序，保证分页顺序确定。

### 7. 用户隔离与软删除过滤

所有列表查询从一开始就有两个固定条件：

```python
Todo.user_id == current_user.id
Todo.deleted_at.is_(None)
```

筛选条件只在这两个条件之后追加。测试会实际插入「其他用户待办」和「已软删除待办」，验证它们都不会泄露到当前用户列表。

### 8. 为什么部分查询校验放在 service 边界

测试发现当前 FastAPI 版本对 BaseModel 查询依赖中的自定义 validator，不会稳定转换为 `RequestValidationError`，可能直接变成 500。

因此查询模型保留 FastAPI 能稳定处理的字段约束，例如页码、枚举、Literal；时区转换、标签清理和时间范围比较在 service 边界完成，并显式转换为 40001 / HTTP 422。

请求体模型的自定义校验仍由 FastAPI 正常包装，不需要改变。

### 9. 本次修复的公共异常序列化问题

Pydantic 自定义错误可能包含：

```python
{"ctx": {"error": ValueError("...")}}
```

`ValueError` 不是 JSON 原生类型，直接 `json.dumps` 会让错误响应再次报错。全局异常处理器现在使用 FastAPI 的 `jsonable_encoder(exc.errors())`，把这类对象安全转换为可序列化内容。

这是所有模块共享的修复，后续日程、记账等自定义校验也会受益。

## 接口示例

### 新建

```http
POST /api/v1/todos
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "写项目周报",
  "due_at": "2026-10-31T15:00:00+08:00",
  "priority": 2,
  "recurrence": "weekly",
  "tags": ["工作", "本周"]
}
```

### 列表

```http
GET /api/v1/todos?page=1&page_size=20&status=pending&tag=工作&sort=due_at&order=asc
Authorization: Bearer <token>
```

响应 `data` 包含：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

## 验证结果

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest --quiet
```

完整后端回归共 42 项测试全部通过。本阶段覆盖：

- 新建成功、标题/标签清理、时间转 UTC；
- 空标题、非法优先级、无时区时间、空标签；
- 新建与列表未登录；
- 跨用户隔离和软删除过滤；
- 状态、时间范围、JSON 精确标签组合筛选；
- 分页、排序、页码/页大小/时间范围非法；
- done 状态筛选。

## 当前边界与下一步

当前只能新建和查询列表，还不能查看单条、修改、删除或完成待办。下一小任务将实现详情、PATCH 修改和软删除，并继续验证越权访问返回 404。
