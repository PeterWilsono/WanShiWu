# 阶段 7.5：统一 AI 创建旅行入口

## 功能与流程

首页 AI 输入现在支持 `create_trip` 动作。模型仍只提出候选，用户在确认卡片中可以修改目的地、天数、预算与旅行偏好；点击确认后，后端重新校验参数，再调用旅行模块的 `create_trip(..., commit=False)`，与 AI 记录在同一事务中提交。

此入口创建的是带标题的空白行程草稿，例如“苏州3日旅行”，不会假装已经生成每日景点安排。用户可进入返回的 `/trip/{id}` 页面继续手动编辑，或使用旅行页面的 AI 草稿生成能力。

## 金额与事务

- `CreateTripArgs.budget` 使用 Decimal，允许 `0`，最多两位小数。
- 后端用 Decimal 精确换算为整数分，不能复用“金额必须大于 0”的记账转换逻辑。
- 前端空预算表示不设置，`0` 表示明确的零预算，两者不会混淆。
- 执行器不直接操作数据表；多动作中任一步失败仍由统一确认服务回滚。
- 行程标记为 `generated_by=ai`、`status=draft`，结果引用为 `trip:{id}`，前端可跳转详情。

## 涉及文件

- `backend/app/assistant/executors.py`：注册 `create_trip` 处理器。
- `backend/tests/test_assistant_confirm_api.py`：覆盖用户编辑、零预算、草稿状态与结果引用；原先“旅行尚未开放”的旧断言已按新功能更新。
- `frontend/src/components/AssistantComposer.vue`：支持旅行确认卡片、预算校验和详情跳转。

## 验证

统一 AI 确认与旅行相关共 29 项后端测试通过，Ruff 通过，前端 TypeScript/Vite/PWA 构建通过。

本阶段没有调用真实模型，也没有据此宣称自然语言意图识别率或真实行程质量已经验收。
