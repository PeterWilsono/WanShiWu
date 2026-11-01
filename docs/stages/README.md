# 阶段说明文档索引

这里用通俗语言记录每个开发小任务：目标、涉及知识、文件职责、运行流程、验证方式和当前边界。详细需求仍以 `docs/PROJECT_SPEC.md` 为准。

| 阶段 | 内容 | 状态 |
|---|---|---|
| [阶段 0](00-project-init.md) | 前后端工程、依赖、代码检查、测试与 Git 初始化 | 已完成 |
| [阶段 1.1](01-1-errors-logging.md) | 统一异常处理与 JSON 结构化请求日志 | 已完成 |
| [阶段 1.2](01-2-database-users.md) | 数据库层、UTC 时间、users 表与 Alembic 迁移 | 已完成 |
| [阶段 1.3](01-3-auth-api.md) | Argon2 密码哈希、注册登录、JWT 与当前用户接口 | 已完成 |
| [阶段 1.4](01-4-frontend-auth-foundation.md) | Axios 拦截器、Token 持久化与 Pinia 登录状态 | 已完成 |
| [阶段 1.5](01-5-login-page-router-guard.md) | 登录页、登录守卫、Token 恢复与安全回跳 | 已完成 |
| [阶段 2.1](02-1-life-models-migration.md) | 待办、日程、分类、交易模型与 Alembic 迁移 | 已完成 |
| [阶段 2.2](02-2-todo-create-list-api.md) | 待办 Schema、新建、分页筛选列表与用户隔离 | 已完成 |
| [阶段 2.3](02-3-todo-detail-update-delete.md) | 待办详情、PATCH 局部更新、状态时间与软删除 | 已完成 |
| [阶段 2.4](02-4-todo-complete-recurrence.md) | 完成待办、周期顺延与数据库事务回滚 | 已完成 |
| [阶段 2.5](02-5-frontend-todo-api-types.md) | 前端待办 TypeScript 类型与六个 API 封装 | 已完成 |
| [阶段 2.6](02-6-frontend-todo-page.md) | 待办列表、筛选分页、新建编辑、完成与删除页面 | 已完成 |
| [阶段 2.7](02-7-event-create-list-api.md) | 日程新建、UTC 校验、重叠时间范围与分页列表 | 已完成 |
| [阶段 2.8](02-8-event-detail-update-delete.md) | 日程详情、PATCH 合并时间校验、用户隔离与软删除 | 已完成 |
| [阶段 2.9](02-9-frontend-event-api-types.md) | 前端日程 TypeScript 类型与五个 API 封装 | 已完成 |
| [阶段 2.10](02-10-frontend-event-page.md) | 日程时间范围列表、新建编辑、删除与响应式页面 | 已完成 |
| [阶段 2.11](02-11-category-management-api.md) | 默认分类初始化、分类 CRUD、唯一性与引用保护 | 已完成 |
| [阶段 2.12](02-12-transaction-create-list-api.md) | 严格整数分账目、新建、用户时区月份与分页筛选 | 已完成 |
| [阶段 2.13](02-13-transaction-detail-update-delete.md) | 账目详情、PATCH 类型分类合并校验与软删除 | 已完成 |
| [阶段 2.14](02-14-frontend-finance-api-types.md) | 前端分类/账目类型、API 与严格元分转换 | 已完成 |
| [阶段 2.15](02-15-frontend-transaction-page.md) | 记账筛选分页、新建编辑、金额组件与软删除页面 | 已完成 |
| [阶段 2.16](02-16-frontend-category-page.md) | 分类管理、内置保护、引用约束与表单交互 | 已完成 |
| [阶段 2.17](02-17-reminders-event-sync.md) | reminders 表、日程提醒同事务联动与迁移回填 | 已完成 |
| [阶段 2.18](02-18-reminder-scheduler-notifications.md) | 每分钟提醒扫描、通知列表与幂等已读 | 已完成 |
| [阶段 2.19](02-19-frontend-notification-center.md) | 未读角标、30 秒轮询、新提醒与已读交互 | 已完成 |
| [阶段 2.20](02-20-monthly-stats-api.md) | 月度收支总览、分类聚合、每日支出与时区边界 | 已完成 |
| [阶段 2.21](02-21-frontend-monthly-stats.md) | 月度统计页面、ECharts 饼图与每日支出折线图 | 已完成 |
| [阶段 2.22](02-22-frontend-calendar.md) | FullCalendar 月历、日程待办分色与详情查看 | 已完成 |
| [阶段 3.1](03-1-assistant-records-model.md) | assistant_records 模型、状态约束、索引与迁移 | 已完成 |
| [阶段 3.2](03-2-llm-client-logs-limit.md) | 统一 LLM Client、超时重试、审计日志与每日限额 | 已完成 |
| [阶段 3.3](03-3-assistant-parse.md) | 工具参数模型、意图 Prompt、FakeLLMClient 与 parse 接口 | 已完成 |
| [阶段 3.4](03-4-assistant-confirm.md) | 确认执行、工具 dispatch、多动作原子事务与幂等 | 已完成 |
| [阶段 3.5](03-5-frontend-assistant-confirmation.md) | 首页 AI 输入、可编辑确认卡片、追问与成功跳转 | 已完成 |
| [阶段 3.6](03-6-assistant-records-cancel-history.md) | AI 历史记录分页筛选、待确认取消与状态约束 | 已完成 |
| [阶段 3.7](03-7-frontend-assistant-cancel.md) | 首页真实取消待确认记录与并发操作防护 | 已完成 |
| [阶段 3.8](03-8-intent-evaluation.md) | 36 条意图评测集、手动真实模型脚本与指标日志 | 已完成 |
| [阶段 4 PWA](04-pwa-support.md) | 应用清单、图标、Service Worker 与离线提示 | 已完成 |
| [阶段 5.1](05-1-pantry-models-migration.md) | 食材批次、购物清单模型、数量约束与迁移 | 已完成 |
| [阶段 5.2](05-2-ingredient-crud-fefo-expiring.md) | 食材 CRUD、FEFO 扣减、库存缺口与用户时区临期 | 已完成 |
| [阶段 5.3](05-3-shopping-items-api.md) | 购物清单 CRUD、完成筛选与菜谱联动 service | 已完成 |
| [阶段 5.4](05-4-frontend-pantry-p0.md) | 库存分组、FEFO 消耗、临期与购物清单页面 | 已完成 |
| [阶段 5.5](05-5-cook-and-recipe-shopping.md) | 做菜多食材原子扣减与缺料批量加入购物清单 | 已完成 |
| [阶段 5.6](05-6-ai-recipe-recommendation.md) | AI 菜谱 JSON 校验、失败重试与真实库存重核算 | 已完成 |
| [阶段 5.7](05-7-assistant-ingredient-confirmation.md) | 首页食材候选编辑、确认入库与多动作回滚 | 已完成 |
| [阶段 6](06-visual-system-refinement.md) | 东方生活手帖视觉系统、响应式导航与月历时区修正 | 已完成 |

后续每完成一个小任务，都会新增对应说明并更新此索引。
