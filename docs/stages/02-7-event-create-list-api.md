# 阶段 2.7：日程新建与时间范围列表接口

## 这一步在做什么

本阶段新增两个后端接口：

| 接口 | 作用 |
| --- | --- |
| `POST /api/v1/events` | 新建一条日程 |
| `GET /api/v1/events` | 按时间窗口查询日程，支持分页 |

日程包含标题、开始和结束时间、全天标记、地点、提前提醒分钟和备注。所有记录仍遵守用户隔离、UTC 时间和软删除过滤。

本阶段最初只保存 `remind_before_min`，提醒记录生成和到点通知分别在后续 2.17、2.18 完成，前端通知交互在 2.19 完成。

## 新建日程的校验规则

- 标题去除首尾空白，必填且最长 200 字；
- `start_at` 必填；
- 开始、结束时间必须带时区，进入数据库前统一转换为 UTC；
- `end_at` 可以省略，但不能早于 `start_at`；
- `remind_before_min` 可以省略，但不能为负数；
- 地点最长 200 字；
- 默认 `all_day = false`。

例如北京时间：

```text
2026-11-10T09:00:00+08:00
```

保存后对应 UTC：

```text
2026-11-10T01:00:00Z
```

## 需要理解的知识

### 1. 单点日程与区间日程

`end_at = null` 表示日程只有一个明确时间点，例如“上午 9 点取快递”。有结束时间的日程则是一个区间，例如会议从 9 点持续到 10 点半。

数据库允许这两种形式，后续日历展示和提醒计算也需要保留这种区别。

### 2. 为什么列表使用“时间重叠”而不是只筛选开始时间

假设查询 11 月 10 日这一天，一场旅行从 11 月 8 日开始、11 月 12 日结束。如果只判断：

```text
start_at 在 11 月 10 日之内
```

这场旅行会被漏掉，但它在 11 月 10 日确实正在进行。

本阶段使用区间重叠条件：

```text
日程有效结束 >= 查询窗口开始
并且
日程开始 <= 查询窗口结束
```

其中“有效结束”是 `end_at`；没有结束时间时使用 `start_at`。

SQLAlchemy 中通过：

```python
func.coalesce(Event.end_at, Event.start_at)
```

实现。`COALESCE` 会返回第一个非空值，正好适合统一处理单点和区间日程。

### 3. 查询参数 range_start / range_end

示例：

```http
GET /api/v1/events?range_start=2026-11-10T00:00:00Z&range_end=2026-11-11T00:00:00Z
```

返回与这个窗口有交集的日程，包括：

- 窗口前开始、窗口内结束；
- 窗口内开始、窗口后结束；
- 覆盖整个窗口；
- 开始时间位于窗口内的单点日程。

窗口完全之前或之后的数据不会返回。反向时间范围、无时区时间和非法分页参数统一返回 HTTP 422 / 业务码 40001。

### 4. 为什么查询模型的部分校验放在 service

FastAPI 当前版本对作为依赖注入的查询 BaseModel 中的自定义 validator 转换不稳定。日程列表与待办列表采用相同策略：

- Schema 保留页码等原生字段约束；
- service 统一转换时区、检查窗口顺序；
- 校验失败抛出 `AppError`，由全局异常处理器返回统一 JSON。

新建日程是请求体，Pydantic 的跨字段 `model_validator` 可以正常工作，因此 `end_at >= start_at` 直接放在 `EventCreate` 中。

### 5. 分页与稳定排序

列表按 `start_at ASC, id ASC` 排序。`id` 是第二排序键，防止两条日程开始时间相同时，在不同页之间顺序不稳定。

响应结构：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 50
}
```

默认每页 50 条，最大 100 条，适合后续日历一次加载一个可见时间窗口。

## 代码如何配合

- `life/schemas.py`：新增 `EventCreate`、`EventListQuery`、`EventResponse`、`EventListResponse`。
- `life/service.py`：新增 `create_event` 和 `list_events`，负责校验转换、重叠条件、用户隔离、软删除过滤与分页。
- `life/router.py`：注册 `/events` 两个路由，只负责依赖注入、调用 service 和统一响应。
- `tests/test_life_events_api.py`：新增成功、参数非法、未登录、跨用户、软删除、重叠范围、排序和分页测试。

## 如何验证

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -v
```

本阶段完整后端回归为 **90 项测试全部通过**，Ruff 检查全部通过。

## 下一步

阶段 2.8 将补齐日程详情、PATCH 修改和软删除，确保修改开始或结束时间后仍然满足时间顺序，越权与不存在继续统一返回 404。
