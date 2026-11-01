# 阶段 5.7：首页 AI 食材入库确认流程

## 目标

把已有的 `add_ingredient` 工具从“能识别但不支持确认”变成完整可用链路：首页一句话解析为食材候选，用户核对并编辑后，确认写入当前用户的食材批次。

## 后端执行链

`assistant/confirm` 的 dispatch 新增 `add_ingredient` 执行器。它复用 `create_ingredient(..., commit=False)`，与待办、日程和账目一样由助手最外层统一提交。

因此，“入库 + 记账”等多动作仍保持原子性：食材已经 flush，但后续账目因分类不存在而失败时，食材和账目都会回滚，不会只留下半条结果。成功后返回 `ingredient:{id}`。

## 前端确认卡片

- 支持食材名称、数量、固定单位、保质期和存放方式编辑。
- 数量必须大于 0，最多两位小数；名称去除首尾空格且不能为空。
- 保留模型原始可选字段，提交时再次由后端 `AddIngredientArgs` 校验。
- 成功结果的“查看食材”跳转 `/pantry`，不再误跳记账页。
- 输入示例增加“买了 6 个鸡蛋放冷藏”。

## 主要文件

- `backend/app/assistant/executors.py`：注册食材执行器并复用 pantry service。
- `backend/tests/test_assistant_confirm_api.py`：食材编辑入库、默认值与多动作回滚；未开放工具测试改用 `save_bookmark`。
- `frontend/src/components/AssistantComposer.vue`：食材草稿字段、表单、校验与结果跳转。

## 验证

- 助手 parse / confirm 测试：17 项通过。
- 后端全量测试：276 项通过。
- Ruff：通过。
- 前端 TypeScript、Vite 和 PWA 构建：通过。
- 浏览器使用模拟模型候选和模拟确认响应验收：将数量从 `6.00` 改为 `6.50` 后，确认请求确实携带 `6.50`、`fridge` 和保质期；随后成功跳转食材页，无控制台错误。真实模型准确率不在本任务中宣称。

## 当前边界

食材工具本身此前已在意图 Prompt 和评测集中，本轮没有修改 Prompt，因此不需要重新运行真实模型评测。买菜同时“记账 + 入库”的多动作已具备执行基础，真实模型表现仍应通过既有评测工具单独验收。
