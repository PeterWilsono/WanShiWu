# 阶段 2.12：账目新建与分页筛选列表接口

## 这一步在做什么

本阶段新增两个记账接口：

| 接口 | 作用 |
| --- | --- |
| `POST /api/v1/transactions` | 新建一条收入或支出记录 |
| `GET /api/v1/transactions` | 按月份、分类、类型筛选，支持排序和分页 |

一条账目包含金额、收支类型、分类、备注、实际发生时间和来源。响应还带有分类摘要，前端不需要逐条追加分类请求。

## 需要理解的知识

### 1. 为什么金额使用严格整数分

后端只接受 `amount_cents`，不接受元，也不接受浮点数：

```json
{
  "amount_cents": 12345
}
```

表示 123.45 元。整数分可以避免 `0.1 + 0.2` 这类二进制浮点误差进入账目。

Schema 使用 `strict=True`，所以 `0`、负数、`12.5`、`12.0`、`true` 和 `null` 都会被拒绝。数据库另有 `amount_cents > 0` 约束作为最后防线。后续前端负责把用户输入的元转换为整数分。

### 2. 为什么分类要同时检查归属和类型

只检查 `category_id` 是否存在不够：

- 其他用户的分类不能拿来记账；
- 支出记录不能使用“工资”这种收入分类；
- 已删除分类不能继续产生新账目。

service 先通过当前用户查询有效分类，再比较 `category.type` 与 `transaction.type`。分类不存在或越权返回 40401，类型不匹配返回 42201，且不会写入账目。

### 3. 月份筛选为什么不能直接拼 UTC 日期

用户看到的是自己时区里的自然月。以 Asia/Shanghai 为例：

```text
2026-11-01 00:00:00+08:00 = 2026-10-31T16:00:00Z
2026-12-01 00:00:00+08:00 = 2026-11-30T16:00:00Z
```

所以查询 `month=2026-11` 时，先把月初和下月初放在用户时区中生成，再转换为 UTC：

```text
occurred_at >= 2026-10-31T16:00:00Z
occurred_at <  2026-11-30T16:00:00Z
```

使用“左闭右开”区间可以避免下月 0 点被重复算进两个月。测试覆盖了北京时间月初和月末的 UTC 边界。

### 4. 查询、排序与分页

支持参数：

- `month=YYYY-MM`；
- `category_id`；
- `type=income/expense`；
- `sort=occurred_at/amount_cents/created_at`；
- `order=asc/desc`；
- `page`、`page_size`，每页最多 100 条。

默认按实际发生时间倒序。排序附加 `id` 作为第二排序键，避免相同时间或金额的记录在不同页之间顺序不稳定。

### 5. 为什么响应包含 category，以及如何避免 N+1

页面通常需要同时显示金额和“餐饮”等分类名，因此响应包含：

```json
{
  "category_id": 1,
  "category": {
    "id": 1,
    "name": "餐饮",
    "type": "expense"
  }
}
```

列表查询使用 SQLAlchemy `selectinload(Transaction.category)` 批量加载分类，避免 20 条账目额外执行 20 次分类查询。

## 代码如何配合

- `life/schemas.py`
  - `TransactionCreate` 校验严格整数分、时间、备注和来源；
  - `TransactionListQuery` 定义筛选、排序和分页；
  - `TransactionResponse` 嵌套分类摘要。
- `life/service.py`
  - 新建前验证分类归属和类型；
  - `month_bounds_utc` 计算用户时区自然月；
  - 列表固定用户隔离与软删除过滤，并批量加载分类。
- `life/router.py`
  - 注册新建和列表接口；
  - 把当前用户时区传给列表 service。
- `tests/test_life_transactions_api.py`
  - 覆盖金额严格性、分类错误、未登录、越权、软删除、月份边界、筛选、排序分页和非法参数。

## 如何验证

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -v
```

本阶段新增 **30 个测试场景**，完整后端回归为 **164 项全部通过**，Ruff 检查全部通过，未安装新依赖。

## 下一步

阶段 2.13 将补齐账目详情、PATCH 局部修改和软删除，并确保修改收支类型或分类后仍保持类型匹配。
