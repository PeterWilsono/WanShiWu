# 阶段 2.8：日程详情、PATCH 修改与软删除

## 这一步在做什么

阶段 2.7 已经能新建日程和查询日程列表。本阶段补齐单条日程的另外三个基本操作：

| 接口 | 作用 |
| --- | --- |
| `GET /api/v1/events/{id}` | 查看一条日程的完整信息 |
| `PATCH /api/v1/events/{id}` | 只修改请求中明确提交的字段 |
| `DELETE /api/v1/events/{id}` | 软删除日程，保留数据库原记录 |

例如，用户只想修改会议地点时，不需要把标题、时间、备注等所有字段重新提交。删除后，日程不会再出现在详情或列表中，但数据库行仍然存在。

## 需要理解的知识

### 1. PATCH 与整体替换有什么区别

`PATCH` 表示局部修改。假设原日程是：

```json
{
  "title": "项目评审会",
  "location": "3 号会议室",
  "note": "准备季度数据"
}
```

只提交：

```json
{
  "location": "5 号会议室"
}
```

结果只改变地点，标题和备注保持原值。如果每次修改都要求提交完整对象，不仅麻烦，还可能因为前端拿着旧数据而覆盖别人刚刚修改的字段。

### 2. “没有传”与“传了 null”不是一回事

本阶段继续使用 Pydantic 的：

```python
data.model_dump(exclude_unset=True)
```

它只保留请求中明确出现的字段：

- 没传 `note`：备注保持原值；
- 传 `"note": null`：清空备注；
- 传 `{}`：不修改任何业务字段。

当前允许显式清空的字段是 `end_at`、`location`、`remind_before_min` 和 `note`。`title`、`start_at` 和 `all_day` 不接受 `null`，因为一条有效日程必须有标题、开始时间和明确的全天标记。

### 3. 为什么修改时间要做“合并校验”

新建日程时可以直接比较请求里的 `start_at` 和 `end_at`。PATCH 更复杂，因为请求可能只包含其中一个。

假设原日程是 9 点到 10 点，现在只提交：

```json
{
  "start_at": "2026-11-10T11:00:00+08:00"
}
```

如果只看请求，请求里没有 `end_at`，似乎无法比较；但数据库里原有结束时间仍是 10 点。直接保存就会产生 11 点开始、10 点结束的错误数据。

因此 service 会先组成“修改后的完整时间”：

```text
新开始时间 = 请求提供则使用请求值，否则使用数据库原值
新结束时间 = 请求提供则使用请求值，否则使用数据库原值
```

然后检查新结束时间不得早于新开始时间，校验通过后才写入。若想把它改成更晚的单点日程，可以先用 `"end_at": null` 清空结束时间，再修改开始时间。

### 4. 为什么越权与不存在返回相同的 404

`get_event` 的查询同时包含：

```text
id = 当前路径 id
user_id = 当前登录用户 id
deleted_at IS NULL
```

所以以下三种情况都会得到 HTTP 404 / 业务码 40401：

- 日程确实不存在；
- 日程属于其他用户；
- 日程已经软删除。

这既能保护数据，也避免通过“403 表示存在但没权限、404 表示不存在”的差异探测其他用户的数据。

### 5. 软删除并不是把行从数据库抹掉

DELETE 只执行：

```text
deleted_at = 当前 UTC 时间
```

原记录仍保留。详情和列表查询统一过滤 `deleted_at IS NULL`，因此用户看不到它，重复删除也返回 404。这样为以后审计、误删恢复或关联数据排查保留了可能。

## 代码如何配合

- `backend/app/modules/life/schemas.py`
  - 新增 `EventUpdate`；
  - 所有字段可省略；
  - 标题和地点自动去首尾空白；
  - 时间必须带时区并转换为 UTC；
  - 提醒分钟不能为负。
- `backend/app/modules/life/service.py`
  - `get_event` 统一处理有效记录查询和 404；
  - `update_event` 使用 `exclude_unset` 局部更新，并在写入前合并校验时间；
  - `delete_event` 写入软删除时间。
- `backend/app/modules/life/router.py`
  - 注册详情、PATCH 和 DELETE 路由；
  - 复用登录依赖、统一响应和 `EventResponse` 序列化。
- `backend/tests/test_life_events_api.py`
  - 增加成功、空 PATCH、显式清空、非法输入、合并时间校验、未登录、越权、不存在和软删除测试。

## 接口示例

修改标题与地点，其他字段不变：

```http
PATCH /api/v1/events/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "季度复盘会",
  "location": "5 号会议室"
}
```

清空结束时间、地点和提醒：

```json
{
  "end_at": null,
  "location": null,
  "remind_before_min": null
}
```

软删除：

```http
DELETE /api/v1/events/1
Authorization: Bearer <token>
```

成功响应为：

```json
{
  "code": 0,
  "message": "删除成功",
  "data": null
}
```

## 如何验证

```bash
cd backend
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -v
```

本阶段新增 **22 个测试场景**，完整后端回归为 **112 项全部通过**，Ruff 格式与代码检查全部通过。测试还直接读取数据库，确认非法修改不会改变原值、越权操作不会修改或删除他人数据、软删除后数据库行仍然存在。

## 当前边界与下一步

说明书要求“修改或删除日程时同步更新或删除提醒”。本阶段先完成 events 表本身的 CRUD，提醒数据层与同事务联动已在后续 2.17 补齐，到点通知在 2.18、2.19 完成。

下一阶段 2.9 将定义前端日程 TypeScript 类型与 API 封装，为日程页面开发做准备。
