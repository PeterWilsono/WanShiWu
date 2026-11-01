# 阶段 5.5：做菜原子扣减与缺料批量联动

## 目标

补齐菜谱业务中最关键的两条写入链路：用户确认“做了这道菜”后一次扣减全部食材；缺少的食材可以整批加入购物清单。两者都必须避免只完成一半。

## 接口

### `POST /api/v1/pantry/cook`

请求包含菜谱名和 `uses` 用量列表。每种食材仍调用既有 FEFO service，按过期日优先跨批次扣减，归零批次自动变为 `used_up`。

所有食材共用同一个数据库事务：任意一项数量不足或单位不匹配，之前已经执行的扣减也全部回滚。错误响应保留 `requested`、`available`、`shortage` 等结构化缺口数据，便于前端准确提示。

### `POST /api/v1/pantry/recipes/shopping-items`

请求包含菜谱名和 `missing` 缺料列表。服务端强制写入 `source=recipe`、当前用户和对应菜谱名，并在一次事务中创建全部购物项，避免前端连续发送多个请求造成部分成功。

## 代码职责

- `backend/app/modules/pantry/schemas.py`：菜谱用量、cook 请求响应、缺料批量请求响应；复用固定单位和 Decimal 数量约束。
- `backend/app/modules/pantry/service.py`：`cook_recipe()` 统一提交或回滚；`add_recipe_missing_to_shopping()` 复用购物 service 批量写入。
- `backend/app/modules/pantry/router.py`：暴露两个需登录接口。
- `backend/tests/test_pantry_cook_api.py`：成功扣减、跨批次 FEFO、重复食材需求、缺口回滚、他人库存隔离、批量加购及数据库异常回滚测试。

## 验证

- 食材相关测试：18 项通过。
- 后端全量测试：264 项通过。
- Ruff：通过。

## 当前边界

单位仍按说明书要求精确匹配，不自动把克换算为千克。菜谱推荐和前端按钮尚未在本小任务接入，因此这两个接口目前是可独立测试的业务能力，不代表页面功能已经完成。
