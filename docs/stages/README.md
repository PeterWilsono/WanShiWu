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
| [阶段 1.6](01-6-registration-page.md) | 独立注册入口、表单校验与注册后自动登录 | 已完成 |
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
| [阶段 5.8](05-8-frontend-recipe-panel.md) | AI 菜谱卡片、做菜扣库存与缺料加购完整页面 | 已完成 |
| [视觉专项](06-visual-system-refinement.md) | 东方生活手帖视觉系统、响应式导航与月历时区修正 | 已完成 |
| [阶段 6.1](06-1-inbox-models-fts.md) | 收藏、标签、每周回顾模型与 FTS5 全文索引迁移 | 已完成 |
| [阶段 6.2](06-2-bookmark-crud-search.md) | 收藏 CRUD、手动标签、用户隔离与 FTS5 搜索 | 已完成 |
| [阶段 6.3](06-3-inbox-fetch-summary.md) | SSRF 防护、异步抓取、AI 摘要标签与手动正文兜底 | 已完成 |
| [阶段 6.4](06-4-weekly-digests.md) | 用户时区周报、幂等生成、调度任务与历史列表 | 已完成 |
| [阶段 6.5](06-5-inbox-frontend-assistant.md) | 收藏页面、导航、搜索筛选、正文兜底与 AI 收藏确认 | 已完成 |
| [阶段 7.1](07-1-trip-models-migration.md) | 行程、每日条目、整数分预算与数据库约束迁移 | 已完成 |
| [阶段 7.2](07-2-trip-crud-budget-reorder.md) | 手动行程、每日预算、单事务重排序与 Markdown 导出 | 已完成 |
| [阶段 7.3](07-3-trip-ai-draft.md) | AI 行程草稿、结构校验、纠错重试与零写库 | 已完成 |
| [阶段 7.4](07-4-trip-frontend.md) | 旅行列表、AI 草稿确认、预算、每日条目、拖拽排序与导出 | 已完成 |
| [阶段 7.5](07-5-trip-assistant-entry.md) | 首页 AI 创建旅行、可编辑确认卡片与零预算支持 | 已完成 |
| [本轮整体回归](08-current-regression.md) | 322 项后端测试、全量 Ruff、前端构建与真实交付边界 | 已完成 |
| [阶段 8.1](08-1-windows-launcher.md) | Windows 双击启动、环境检查、自动迁移与浏览器入口 | 已完成 |
| [阶段 8.2](08-2-docker-ci-backup.md) | Docker Compose、CI 覆盖率门槛与 SQLite 在线备份 | 已完成 |
| [阶段 9.1](09-1-model-settings-backend.md) | MiMo / DeepSeek 按用户配置、密钥加密、模型切换与连接测试 | 已完成 |
| [阶段 9.2](09-2-profile-settings-frontend.md) | 我的、设置导航、模型配置表单、通用偏好与启动兼容 | 已完成 |
| [阶段 10.1](10-1-structured-ai-output.md) | 菜谱/摘要/行程 JSON 围栏兼容、宽松边界与严格业务校验 | 已完成 |
| [阶段 10.2](10-2-inbox-fetch-rescue.md) | 网页编码/XHTML/正文兜底、失败原因与仅保存正文 | 已完成 |
| [阶段 10.3](10-3-trip-ai-entry.md) | 旅行列表与空状态的 AI 直接入口、弹窗初始模式 | 已完成 |
| [阶段 10.4](10-4-empty-inventory-recipes.md) | 空库存自由菜谱、完整采购用料、购物清单联动与明确提示 | 已完成 |
| [阶段 11.1](11-1-windows-desktop-installer.md) | Electron 静默桌面窗口、内嵌 Python/SQLite、NSIS 安装与实际安装验收 | 已完成 |
| [阶段 11.2](11-2-desktop-restart-proxy-cache.md) | 修复代理与旧 PWA 缓存导致的二次启动失败，1.0.1 覆盖升级验证 | 已完成 |
| [阶段 11.3](11-3-affirmations-close-cleanup.md) | 48 条首页小签、关闭确认、项目瘦身与 GitHub 上传检查 | 已完成（4 个旧构建目录待手动清理） |
| [阶段 12.1](12-1-github-public-release.md) | 用户首页、开发文档拆分、公开仓库、CI 验收与安装包 Release | 已完成 |

后续每完成一个小任务，都会新增对应说明并更新此索引。
