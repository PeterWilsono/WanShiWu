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

后续每完成一个小任务，都会新增对应说明并更新此索引。
