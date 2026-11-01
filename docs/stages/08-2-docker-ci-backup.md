# 阶段 8.2：Docker、CI 与 SQLite 备份

## 这一阶段补齐什么

说明书主路线不仅要求能开发，还要求便于在新环境启动、持续验证和保护数据。本阶段补齐此前只有名称、没有实际文件的交付能力。

## Docker Compose

- `backend/Dockerfile`：Python 多阶段构建，运行阶段使用非 root 用户。
- `frontend/Dockerfile`：Node 构建 Vue/PWA，Nginx 提供静态文件。
- `frontend/nginx.conf`：SPA 路由回退，并把 `/api` 代理到 `backend:8000`；AI 请求代理超时为 120 秒。
- `docker-compose.yml`：后端先执行 Alembic 迁移，再启动 Uvicorn；前端等待后端健康检查通过。
- SQLite 使用 `wanshiwu-data` 命名卷挂载到 `/app/data`，容器重建不会直接删除数据库。
- Compose 变量可在根目录 `.env` 配置。公网部署必须更换默认 JWT 密钥。

安装 Docker 后，从根目录执行 `docker compose up --build`，访问 `http://127.0.0.1:5173`。

## CI

`.github/workflows/ci.yml` 分为后端和前端两个任务：

- 后端安装锁定环境，运行 Ruff、完整 pytest、覆盖率报告，低于 80% 失败。
- 前端使用 Node 24、`npm ci` 和 `npm run build`。
- 推送 main 和 Pull Request 都会触发。

## 安全备份

`scripts/backup_db.py` 使用 SQLite Online Backup API，而不是在数据库写入期间直接复制文件。它先写临时文件，执行 `PRAGMA integrity_check`，通过后原子改名为正式备份；源文件不存在、目标已存在或把源文件当目标都会拒绝，不自动删除旧备份。

```bash
backend\.venv\Scripts\python.exe scripts\backup_db.py
```

默认源为 `backend/data/wanshiwu.db`，目标为 `backups/wanshiwu-时间.db`，可用参数覆盖。

## 实际验证

- 新增 2 项备份测试通过，真实开发数据库也完成一次在线备份和完整性检查。
- 完整后端：**324 项测试通过，总覆盖率 96.25%**，达到 CI 的 80% 门槛。
- Ruff 全量通过；Compose 与 CI 均通过 YAML 解析。
- 测试中有 3 条既有 SQLite ResourceWarning，不影响通过结果，但可作为后续清理项。
- 当前机器没有 Docker 命令，因此未实际执行镜像构建、Compose 启动或 Nginx 容器内验证，不能宣称全新 Docker 环境已验收。
