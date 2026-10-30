# 阶段 2.1：生活管家数据模型与 Alembic 迁移

## 这一阶段在做什么

阶段 2 开始实现生活管家。本阶段先不碰页面和接口，而是建立四张业务表：

- `todos`：待办，包括截止时间、优先级、状态、周期和标签。
- `events`：日程，包括开始/结束时间、全天、地点和提前提醒。
- `categories`：收支分类，区分收入与支出，支持内置和自定义。
- `transactions`：收支记录，保存整数分金额、分类、发生时间和来源。

先把表结构、约束和索引稳定下来，后续 CRUD service 和 API 就有可靠基础。

## 主要文件

- `backend/app/modules/life/models.py`：四个 SQLAlchemy 模型与业务枚举。
- `backend/app/modules/life/__init__.py`：生活管家模块入口。
- `backend/app/db/base.py`：新增 `UserOwnedMixin`，统一业务表的 `id` 和 `user_id`。
- `backend/alembic/env.py`：注册 life 模型，让 Alembic 能发现新表。
- `backend/alembic/versions/2e7733437d1c_create_life_tables.py`：四张表的真实迁移。
- `backend/tests/conftest.py`：测试建表时注册 life 模型。
- `backend/tests/test_life_models.py`：模型、约束和索引测试。

## 四张表分别记录什么

### 1. todos

除了通用的 `id / user_id / created_at / updated_at / deleted_at`，主要有：

- `title`、`note`：标题与备注；
- `due_at`：可空的截止时间；
- `priority`：1 低、2 中、3 高，默认 2；
- `status`：pending、done、cancelled；
- `completed_at`：完成时间；
- `recurrence`：none、daily、weekly、monthly；
- `tags_json`：JSON 字符串数组，例如 `["工作", "本周"]`。

周期性规则现在只保存字段，「完成后自动生成下一次」会在对应业务任务实现。

### 2. events

`start_at` 必填，`end_at` 可空，但不能早于开始时间。`all_day` 表示全天日程，`remind_before_min` 表示提前多少分钟提醒，空值表示不设置。

提醒调度器不在本阶段实现，目前只保存未来需要的配置。

### 3. categories

`type` 分为 income 和 expense。同一用户、同一类型下，分类名称唯一：

```text
用户 A + expense + 其他  → 只能有一条
用户 A + income  + 其他  → 可以存在
用户 B + expense + 其他  → 也可以存在
```

`is_default` 用来区分内置分类与自定义分类。默认分类的初始化、禁止删除等规则属于后续 service，不靠模型字段自动完成。

### 4. transactions

- `amount_cents`：正整数，单位为分；
- `type`：收入或支出，方向不通过正负金额表示；
- `category_id`：指向 categories 的外键；
- `occurred_at`：实际发生时间；
- `source`：manual、assistant、pantry、trip，说明记录从哪里产生。

模型还定义了 `transaction.category` 关系，后续可以直接读取分类资料，不必每次手写 join。

## 用到的主要知识

### 1. Mixin 如何减少通用字段重复

`UserOwnedMixin` 提供 `id` 和 `user_id`，`TimestampMixin` 提供创建/更新时间，`SoftDeleteMixin` 提供删除时间。四个模型组合这些 Mixin 后再继承 `Base`。

这样通用规则只写一次，未来其他模块也能复用。`user_id` 同时是指向 users 的外键并带索引，为资源归属检查和按用户查询做准备。

### 2. Python Enum 与数据库字符串

项目要求代码使用枚举，数据库保存字符串。直接使用 SQLAlchemy Enum 时，默认可能保存枚举成员名（如 `PENDING`），而说明书要求保存值（如 `pending`）。

`enum_values()` 明确把 `.value` 列表交给 SQLAlchemy，因此：

- Python 中获得类型明确的 `TodoStatus.PENDING`；
- SQLite 中保存易读、与接口一致的 `pending`；
- 开启约束后，数据库也拒绝不在枚举范围内的值。

### 3. 为什么金额不能用浮点数

二进制浮点无法精确表示某些十进制小数，长期累计可能出现 0.01 元误差。项目把 12.34 元保存为整数 `1234` 分，计算和汇总都使用整数，只有前端展示时转换回元。

`BIGINT` 能容纳较大的整数金额，`CheckConstraint(amount_cents > 0)` 则阻止零或负数。收入/支出方向由 `type` 决定。

### 4. 数据库 CheckConstraint 与接口校验的关系

接口层的 Pydantic 校验负责给用户提供清晰、即时的错误提示；数据库约束是最后防线，防止脚本、迁移或其他代码路径写入非法数据。

本阶段加入：

- 待办优先级必须在 1～3；
- 日程结束时间不能早于开始时间；
- 提前提醒分钟不能为负；
- 交易金额必须大于 0；
- 枚举字段只能保存允许值。

后续接口仍然需要校验，不能因为数据库有约束就省略友好错误。

### 5. 外键保证什么、不保证什么

`transactions.category_id → categories.id` 可以阻止交易引用一个不存在的分类。但它不会自动判断「交易所属用户」和「分类所属用户」是否相同，也不会检查交易类型与分类类型是否一致。

这两条跨字段、跨记录的业务规则将在记账 service 中检查，并配越权与类型不匹配测试。

### 6. 复合索引与最左前缀

例如 `(user_id, status, due_at)` 适合「查询某用户的待办，再按状态筛选、按截止时间排序」。复合索引的列顺序来自说明书中的典型查询，不是把三个字段随意放在一起。

索引会占用少量空间并增加写入成本，所以只给外键和常用筛选/排序字段建立，不为每一列盲目添加。

本阶段核对了：

- todos：`(user_id, status, due_at)`；
- events：`(user_id, start_at)`；
- transactions：`(user_id, occurred_at)`、`(user_id, category_id)`；
- categories：唯一 `(user_id, type, name)`。

### 7. 软删除与物理删除

所有四张表都有可空 `deleted_at`。后续 DELETE API 通常只写入这个时间，查询时过滤 `deleted_at IS NULL`，便于恢复、审计和避免历史统计突然消失。

模型字段本身不会自动过滤查询，后续 service 必须同时带 `user_id` 和 `deleted_at IS NULL`，不能依赖数据库「默认看不见」。

### 8. Alembic 自定义类型为什么要人工审查

`UTCDateTime` 是项目自定义类型。Alembic 自动生成了 `app.db.types.UTCDateTime(...)`，但没有自动加入对应 import。如果不审查，全新环境执行迁移会出现 `NameError`。

本阶段补上 `import app.db.types` 后，已实际执行 `alembic upgrade head`，确认四张表在真实 D 盘 SQLite 数据库中创建成功。自动生成不代表可以直接提交，迁移必须审查并实际运行。

## 如何验证

```bash
cd backend
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -v
```

本阶段完成后共 27 项测试全部通过，其中生活模型新增 8 项，覆盖：

- 四表创建、默认值、UTC 时间、JSON 标签和分类关系；
- 指定复合索引与分类唯一约束；
- 分类唯一性的用户/类型范围；
- 无效分类外键；
- 非正金额；
- 日程结束时间早于开始时间；
- 负提醒分钟；
- 越界待办优先级。

## 当前边界与下一步

现在只有数据层，没有默认分类初始化、CRUD、分页筛选和前端页面。下一小任务将实现生活管家的 Pydantic Schema 与基础 service 规则，优先从待办的新建和列表流程开始。
