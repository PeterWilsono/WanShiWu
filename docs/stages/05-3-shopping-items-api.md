# 阶段 5.3：购物清单管理接口

## 目标

提供不依赖 AI 的购物清单完整管理能力，也为后续菜谱缺料一键联动准备 service 入口。

## 实现内容

- `POST /api/v1/shopping-items`：添加名称、可选数量和单位；默认未完成、来源 manual。
- `GET /api/v1/shopping-items`：分页并按 done、source 筛选；未完成项优先，组内按创建时间倒序。
- `PATCH /api/v1/shopping-items/{id}`：可修改名称、数量、单位、来源和菜谱名，也可勾选/取消完成。
- `DELETE /api/v1/shopping-items/{id}`：软删除，不物理抹掉记录。
- `create_shopping_item()` 支持 `commit=False`，后续菜谱缺料可以在需要时由外层统一控制事务。

## 细节

PATCH 使用 `exclude_unset=True`，所以“没有传 quantity”和“明确传 quantity=null”不同：前者保留原值，后者清空数量。列表、修改、删除全部带当前用户条件，其他用户的记录按不存在处理。

## 验证

专项 4 项通过，覆盖新建默认值、来源与完成状态筛选、勾选完成、显式 null、软删除、未登录、参数错误和越权访问。完整后端回归 257 项全部通过。

## 当前边界

本任务尚未提供前端页面，也没有“菜谱缺料加入”按钮；联动所需的后端基础已经就绪。
