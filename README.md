# 万事屋 WanShiWu

> 个人生活效率平台 —— 统一 AI 入口 + 四个可插拔模块：生活管家 · 食材管家 · 收藏箱 · 旅行规划

对万事屋说一句话（如"明天下午三点约了牙医"），系统理解后生成确认卡片，确认后自动记录到对应模块。**AI 提议、人确认** —— 模型只负责理解，写库一律由确定性业务代码完成。

## 技术栈

| 端 | 技术 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy 2.0 · Alembic · SQLite(WAL) · Pydantic v2 |
| 前端 | Vue 3 · TypeScript · Vite · Element Plus · Pinia · Vue Router |
| AI | OpenAI 兼容接口（DeepSeek / 通义千问），function calling 意图识别 |
| 工程 | pytest · ruff · GitHub Actions · Docker Compose |

## 快速开始（开发模式）

```bash
# 1. 后端
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
copy .env.example .env          # 填入你的 LLM_API_KEY
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 2. 前端
cd frontend
npm install
npm run dev                     # http://localhost:5173

# 3. 测试
cd backend && pytest
```

## 项目状态

- [x] 阶段 0 · 项目初始化
- [x] 阶段 1 · 骨架与登录
- [ ] 阶段 2 · 生活管家（无 AI）
- [ ] 阶段 3 · AI 入口
- [ ] 阶段 4 · 提醒、统计、PWA —— MVP
- [ ] 阶段 5 · 食材管家
- [ ] 阶段 6 · 收藏箱
- [ ] 阶段 7 · 旅行规划
- [ ] 阶段 8 · 交付（Docker / CI / 文档）

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
