# 万事屋 WanShiWu

> 个人生活效率平台 —— 统一 AI 入口 + 四个可插拔模块：生活管家 · 食材管家 · 收藏箱 · 旅行规划

对万事屋说一句话（如"明天下午三点约了牙医"），系统理解后生成确认卡片，确认后自动记录到对应模块。**AI 提议、人确认** —— 模型只负责理解，写库一律由确定性业务代码完成。

## 技术栈

| 端 | 技术 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy 2.0 · Alembic · SQLite(WAL) · Pydantic v2 |
| 前端 | Vue 3 · TypeScript · Vite · Element Plus · Pinia · Vue Router |
| AI | OpenAI 兼容接口（小米 MiMo / DeepSeek），function calling 意图识别 |
| 工程 | pytest · ruff · GitHub Actions · Docker Compose |
| 桌面软件 | Electron · PyInstaller · NSIS Windows 安装包 |

## Windows 桌面软件（推荐给普通使用者）

构建产物：`desktop/release/万事屋-Windows-1.0.0-安装包.exe`，约 160 MB。

1. 只需把这一个 exe 安装包发给使用 Windows 10/11 64 位系统的朋友。
2. 双击安装包，按普通软件完成安装，然后双击桌面“万事屋”图标。
3. 首次打开点击“创建账号”。不需要 Python、Node.js、浏览器地址或命令行窗口。
4. 普通功能在本机运行；AI 和网页收藏需要网络，AI 还需在“我的 → 设置 → AI 模型”配置自己的 Key。

账号与业务数据默认保存在 `%LOCALAPPDATA%\WanShiWu\data`，不同电脑的数据不会自动同步。备份时先完全退出软件，再复制整个 `data` 目录。当前安装包未购买商业代码签名证书，Windows 可能显示“未知发布者”；正式公开分发前建议增加可信代码签名。

开发者重新构建：先安装后端开发依赖、`desktop/requirements-build.txt` 和 `desktop` 的 npm 依赖，再在项目根目录运行 `desktop\build-windows.bat`。安装包、缓存、测试数据库和构建目录均不提交 Git。

## 快速开始（开发模式）

### Windows 最简单的方式（推荐）

1. 打开项目文件夹 `D:\cursor\wanshiwu-001`。
2. **双击根目录的 `start-dev.bat`**，不要双击 `frontend/index.html`。
3. 脚本会检查环境、执行数据库迁移，分别打开后端和前端窗口，然后自动打开浏览器。
4. 浏览器地址是 **http://127.0.0.1:5173**。首次使用点击“创建账号”。
5. 使用期间保留 `WanShiWu Backend` 和 `WanShiWu Frontend` 两个窗口；关闭这两个窗口即停止服务。

`backend/.env` 不存在时脚本会从示例自动复制。手动功能无需模型 Key；要使用 AI，登录后点击右上角头像，进入 **“我的 → 设置 → AI 模型”**，分别配置 MiMo 或 DeepSeek 并测试连接，无需手动编辑文件。只想检查环境而不启动服务，可在项目目录运行 `start-dev.bat --check`。

### 手动启动方式

```bash
# 1. 后端
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
copy .env.example .env          # 可选：AI 也可登录后在“我的 → 设置”配置
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 2. 前端
cd frontend
npm install
npm run dev                     # http://localhost:5173

# 3. 测试
cd backend && pytest
```

### Docker Compose（已安装 Docker 时）

```bash
docker compose up --build
```

浏览器仍访问 **http://127.0.0.1:5173**。后端启动前自动执行 Alembic 迁移，前端 Nginx 将 `/api` 转发到后端；SQLite 数据保存在 `wanshiwu-data` 命名卷中，删除容器不会直接删除数据。可在项目根目录 `.env` 设置 `JWT_SECRET`、`LLM_API_KEY` 等 Compose 变量；部署到公网前必须更换默认 JWT 密钥。

当前开发机未安装 Docker，因此配置与 YAML 语法已检查，但容器构建和启动尚未本机验收。

### 数据库备份

在项目和现有虚拟环境均已准备好的情况下，从根目录运行：

```bash
backend\.venv\Scripts\python.exe scripts\backup_db.py
```

备份默认写入 `backups/`，使用 SQLite Online Backup API，并通过 `PRAGMA integrity_check` 后才生成正式文件；不会覆盖已有备份。可用 `--source` 和 `--output` 指定源数据库与目标文件。

CI 位于 `.github/workflows/ci.yml`，包含后端 Ruff、pytest 和 80% 覆盖率门槛，以及前端依赖安装与生产构建。

## 项目状态

- [x] 阶段 0 · 项目初始化
- [x] 阶段 1 · 骨架、登录与自主注册
- [x] 阶段 2 · 生活管家：待办、日程、分类记账、提醒、月历与月度统计
- [x] 阶段 3 · 统一 AI 入口：解析、可编辑确认、原子写入、历史与取消
- [x] 阶段 4 · PWA 基础能力
- [x] 阶段 5 · 食材管家 P0/P1：库存、临期、购物、做菜扣减与 AI 菜谱
- [x] 阶段 6 · 收藏箱 P0/P1：标签、全文搜索、安全抓取、AI 摘要与每周回顾
- [x] 阶段 7 · 旅行规划 P0/P1：每日安排、预算、AI 草稿、重排序与 Markdown 导出
- [x] 阶段 8 · 一键启动、Docker/Compose、CI、备份脚本与项目文档
- [x] 阶段 9 · 我的与设置：MiMo / DeepSeek 配置、加密密钥、连接测试与通用偏好
- [x] 阶段 11 · Windows 桌面软件：内嵌后端、静默启动、本地数据与 NSIS 安装包

当前四个模块的 P0/P1 主要流程均已落地，但不等于说明书全部版本已经完成。RAG 知识库、PDF/ICS 导出、地图与路线等 P2 增强尚未实现；真实模型质量、真实网页抓取、浏览器细节交互和真机 PWA 仍需单独验收。各小阶段的真实验证记录见阶段文档。

首次打开 `http://127.0.0.1:5173` 后，可在登录页切换到“创建账号”，注册成功会自动进入首页。

## 文档

- [项目说明书（唯一权威）](docs/PROJECT_SPEC.md) —— 需求、架构、数据库、接口、AI 层、开发路线
- [阶段说明文档](docs/stages/README.md) —— 每个小任务的目标、知识点、实现方式与验证结果
- 开发日志：`docs/devlog.md`（随开发补充）
- 评测记录：`docs/eval_log.md`（阶段 3 起）

## 设计要点

- **AI 提议、人确认**：parse 只理解不执行，confirm 经 Pydantic 二次校验后由 service 层写库
- **LLM 只理解不执行 / 数字让代码算**：金额全程整数分，汇总、预算、过期日期均由代码计算
- **模块化单体**：模块间仅通过 service 层调用，dispatch 表实现可插拔
- **可观测**：所有 LLM 调用写日志（耗时 / token / 成败），每日限额，评测集量化准确率

## 关联远程仓库

本地开发已完成 `git init`。远程 GitHub 仓库创建后：

```bash
git remote add origin <你的仓库地址>
git push -u origin main
```
