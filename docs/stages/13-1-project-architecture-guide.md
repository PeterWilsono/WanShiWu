# 阶段 13.1：项目技术架构通俗 Word 教程

## 目标

基于当前源码生成一份面向初学者的完整 Word 教程，帮助项目作者理解功能从页面、网络、后端到数据库的完整链路，而不是只罗列技术名词。

## 内容范围

- Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router、Axios。
- FastAPI、Uvicorn、Pydantic、SQLAlchemy、Alembic、APScheduler。
- HTTP/HTTPS、REST、JSON、JWT Bearer、代理、端口和同源策略。
- 模块化单体与分布式的区别；明确当前未使用微服务、Redis、消息队列和 Kubernetes。
- SQLite、WAL、外键、软删除、事务、整数分、FEFO、FTS5。
- 17 张普通 ORM 表和 1 张全文检索虚拟表的关系。
- 当前 OpenAPI 的 72 个操作，按业务模块完整列出。
- AI parse/confirm、DISPATCH、模型日志、重试、限额和密钥加密。
- Electron、PyInstaller、NSIS、Docker Compose、Nginx。
- pytest 隔离数据库、FakeLLM、342 个测试用例、80% 覆盖率门槛和 GitHub Actions。
- 源码阅读顺序、构建过程、FAQ 和真实能力边界。

## 实现方式

重新审查当前前后端、桌面、数据库和测试源码，避免沿用旧阶段数量。以“用户输入一句话到确认入库”为贯穿案例，每个技术概念同时给出专业定义、大白话和项目位置。

使用 Word 创作流水线生成 Markdown、专业 HTML 和 DOCX。成品采用 A4、独立封面、目录、正文页码、分级标题、统一表格和等宽代码样式。

## 验证

- Markdown 格式门禁通过：单一主标题、无裸 HTML、标准表格和代码块。
- DOCX 转换预检通过，页面要素完整。
- 成品验证通过：664 项内容检查无缺失，目录域存在，70 个 PAGEREF，71 个标题样式绑定，封面与目录分节、正文页码重起正常。
- 成品路径：`output/e8ec5a19-384e-4946-a63d-2651e286bf48/stage3/万事屋项目技术架构通俗解读.docx`。

本次未修改业务代码，也未重新宣称运行了一轮新测试；测试数量与通过状态引用当前源码静态盘点和已有发布验收记录。
