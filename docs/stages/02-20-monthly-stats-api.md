# 阶段 2.20：月度收支与每日支出统计 API

## 这一步做什么

新增两个只读接口，让前端不必自己遍历账本来计算统计结果：

- `GET /api/v1/stats/monthly?month=YYYY-MM`：返回月收入、月支出、结余和分类金额汇总。
- `GET /api/v1/stats/daily?month=YYYY-MM`：返回该月每一天的支出，没有账目的日期补 0。

两个接口都要求登录，`month` 必须类似 `2026-03`。金额全部是整数分，`balance_cents = income_cents - expense_cents`，所以支出大于收入时节余可以为负数。

## 为什么月份边界不能直接用 UTC

数据库统一存 UTC 时间，但用户说的“3 月”指自己时区里的 3 月。例如上海时间 `2026-03-01 00:00` 在数据库中是 `2026-02-28 16:00 UTC`。如果直接按 UTC 月份筛选，这笔账就会错误地落入 2 月。

实现复用了账目列表的 `month_bounds_utc()`：先在用户时区构造月初和下月月初，再转成 UTC，使用“包含月初、不包含下月月初”的左闭右开区间查询。

## 聚合方式

- 月度总收支：SQL 按 `type` 使用 `GROUP BY` 汇总。
- 分类统计：SQL 连接 categories，按分类和收支类型汇总；不按分类的软删除状态过滤，因为历史账目仍应保留统计含义。
- 每日支出：查询当月支出后，把每笔发生时间转换到用户时区，再按当地日期累加。这里没有直接套用 SQLite 的固定小时偏移，因为固定偏移在夏令时切换的时区会归错日期。
- 每日响应补齐自然月的所有日期，因此前端折线图不会把“没有消费”误画成“缺少数据”。

所有查询都限定 `user_id`、`deleted_at IS NULL` 和本月的 UTC 区间，其他用户、已删除账目和月份外记录均不参与统计。

## 改动文件

- `backend/app/modules/life/schemas.py`：月份查询、月度统计、分类统计、每日统计响应模型。
- `backend/app/modules/life/service.py`：月度 SQL 聚合、用户时区每日汇总和整月补零。
- `backend/app/modules/life/router.py`：注册 `/stats/monthly` 与 `/stats/daily`。
- `backend/tests/test_life_stats_api.py`：新增 4 个测试函数，覆盖多种成功与失败场景。

每日响应对外字段仍为 `date`；Pydantic 内部使用 `day` 避免字段名遮蔽日期类型，序列化时通过别名输出。

## 如何验证

在 backend 环境中运行：

```bash
python -m pytest tests/test_life_stats_api.py -q
python -m pytest tests -q
python -m ruff check app tests
python -m ruff format --check app tests
```

专项测试 4 项通过，完整后端回归 **209 项全部通过**。测试覆盖了用户时区月末月初、分类与总收支、其他用户隔离、软删除过滤、每日合并与补零、空月份、未登录、缺少月份和非法月份。

## 当前边界

本任务只提供数据接口，尚未实现统计页面和图表；不涉及预算、超支预警或导出 CSV，它们属于后续独立任务。
