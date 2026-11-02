# 万事屋开发文档

本文由原 README 改名并整理，保留开发、测试、部署和打包说明。普通使用者请访问[项目首页与下载说明](README.md)。

## 技术栈

| 端 | 技术 |
| --- | --- |
| 后端 | Python 3.11+、FastAPI、SQLAlchemy 2、Alembic、SQLite（WAL）、Pydantic v2 |
| 前端 | Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router |
| AI | OpenAI 兼容接口（MiMo / DeepSeek）、结构化输出与意图识别 |
| 工程 | pytest、Ruff、GitHub Actions、Docker Compose |
| 桌面软件 | Electron、PyInstaller、NSIS Windows 安装包 |

## Windows 一键开发启动

1. 克隆项目并进入项目根目录。
2. 安装 Python 3.11+ 和 Node.js，准备后端虚拟环境及前后端依赖。
3. 双击根目录的 `start-dev.bat`，不要直接双击 `frontend/index.html`。
4. 脚本会检查环境、执行数据库迁移，分别启动后端和前端，然后打开浏览器。
5. 浏览器地址为 `http://127.0.0.1:5173`，首次使用点击“创建账号”。
6. 使用期间保留 `WanShiWu Backend` 和 `WanShiWu Frontend` 两个窗口。

`backend/.env` 不存在时，脚本会从示例复制。普通功能无需模型 Key；使用 AI 时，登录后进入“我的 → 设置 → AI 模型”配置并测试连接。只检查环境可运行：

```bash
start-dev.bat --check
```

## 手动启动

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:app --reload
```

接口文档位于 `http://localhost:8000/docs`。

### 前端

另开终端：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

### 测试与构建

```bash
cd backend
pytest
ruff check .

cd ../frontend
npm run build
```

CI 位于 `.github/workflows/ci.yml`，包含后端 Ruff、pytest 和 80% 覆盖率门槛，以及前端依赖安装与生产构建。

## Docker Compose

```bash
docker compose up --build
```

浏览器访问 `http://127.0.0.1:5173`。后端启动前自动执行 Alembic 迁移，前端 Nginx 将 `/api` 转发到后端，SQLite 数据保存在 `wanshiwu-data` 命名卷中。

可在项目根目录 `.env` 设置 `JWT_SECRET`、`LLM_API_KEY` 等 Compose 变量；部署到公网前必须更换默认 JWT 密钥。当前开发机未安装 Docker，因此配置与 YAML 语法已检查，但容器构建和启动尚未本机验收。

## Windows 桌面软件

普通用户从 [GitHub Releases](https://github.com/PeterWilsono/WanShiWu/releases/latest) 下载，不需要以下开发环境。

开发者重新构建：

1. 安装后端开发依赖和 `desktop/requirements-build.txt`。
2. 在 `desktop/` 安装 npm 依赖。
3. 构建前端生产文件。
4. 在项目根目录运行 `desktop\build-windows.bat`。

安装包、缓存、测试数据库和构建目录均不提交 Git。Windows 安装包约 160 MB，应上传到 GitHub Release，不要放入源码历史。

桌面版账号与业务数据默认保存在 `%LOCALAPPDATA%\WanShiWu\data`。备份时先完全退出软件，再复制整个 `data` 目录。普通功能在本机运行；AI 和网页收藏需要网络，AI 还需用户配置自己的 Key。

## 数据库备份

在项目和现有虚拟环境均已准备好的情况下，从根目录运行：

```bash
backend\.venv\Scripts\python.exe scripts\backup_db.py
```

备份默认写入 `backups/`，使用 SQLite Online Backup API，并通过 `PRAGMA integrity_check` 后才生成正式文件；不会覆盖已有备份。可用 `--source` 和 `--output` 指定源数据库与目标文件。

## 项目状态

- [x] 项目骨架、登录与自主注册
- [x] 生活管家主要流程
- [x] 统一 AI 入口与确认执行
- [x] PWA 基础能力
- [x] 食材管家主要流程
- [x] 收藏箱主要流程
- [x] 旅行规划主要流程
- [x] 一键启动、CI、备份和项目文档
- [x] 模型设置与加密存储
- [x] Windows 桌面软件与安装包

四个模块的主要流程已经落地，但不代表说明书全部版本已经完成。RAG 知识库、PDF/ICS 导出、地图与路线等增强项尚未实现；真实模型质量、真实网页抓取、浏览器细节交互和真机 PWA 仍需单独验收。

## 设计要点

- **AI 提议，人确认**：解析不直接执行，确认经 Pydantic 二次校验后由 service 层写库。
- **数字让代码计算**：金额使用整数分，汇总、预算、过期日期由代码计算。
- **模块化单体**：模块间通过 service 层调用，dispatch 表实现可插拔。
- **可观测**：记录模型调用耗时、Token、成败和每日限额，并提供意图评测集。

## 文档

- [项目首页与下载](README.md)
- [项目需求说明书](docs/PROJECT_SPEC.md)
- [阶段开发记录](docs/stages/README.md)
- [项目概览](docs/PROJECT_OVERVIEW.md)
- [GitHub 维护指南](docs/GITHUB_SETUP.md)
- 开发日志：`docs/devlog.md`
- 评测记录：`docs/eval_log.md`

## 许可证与作者

本项目采用 [MIT License](LICENSE)。作者：云程 / [PeterWilsono](https://github.com/PeterWilsono)。
