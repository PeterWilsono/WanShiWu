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

后续每完成一个小任务，都会新增对应说明并更新此索引。
