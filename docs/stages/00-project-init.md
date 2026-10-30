# 阶段 0：项目初始化

## 这一阶段在做什么

阶段 0 不实现具体业务，而是把后续开发需要的「地基」搭好：确定目录、安装并锁定依赖、建立前后端最小应用、配置代码检查和测试、建立 Git 版本记录。

可以把整个项目想成盖房子：这一阶段还没有卧室和厨房，但已经有地基、施工图纸、水电入口和检查工具。后面的功能都在这套结构上增加，避免边做边改工程规则。

## 完成后有什么

- `docs/PROJECT_SPEC.md`：项目说明书的 Markdown 版本，是开发时查阅的权威依据。
- `backend/`：Python + FastAPI 后端，已经提供 `GET /api/v1/health` 健康检查接口。
- `frontend/`：Vue 3 + TypeScript 前端，首页能显示「万事屋」。
- `backend/tests/`：自动化测试，能通过代码验证接口是否正常。
- `.gitignore`、`.env.example`、README 和 Git 首次提交：让项目可维护、可备份，也避免把密码等敏感内容提交进去。

## 用到的主要技术与知识

### 1. 前后端分离

前端负责浏览器里的页面和交互，后端负责数据、业务规则和安全校验。两者通过 HTTP API 通信，例如前端请求 `/api/v1/health`，后端返回 JSON。

这样做的好处是职责清晰：页面怎么显示不影响数据库怎么存，后端业务也能独立测试。

### 2. FastAPI 与 Uvicorn

- FastAPI 是编写 API 的 Python 框架，负责路由、参数校验和接口文档。
- Uvicorn 是运行 FastAPI 应用的服务器程序。
- 访问 `http://localhost:8000/docs` 可以看到自动生成的 Swagger 接口文档。

### 3. Vue 3、TypeScript 与 Vite

- Vue 3 用来构建页面和组件。
- TypeScript 给 JavaScript 增加类型，例如提前发现「把数字当字符串传」的问题。
- Vite 负责前端开发服务器和打包构建。
- Element Plus 是已选定的 UI 组件库，后续表格、表单、弹窗都使用它，不再混用另一套组件库。

### 4. 统一响应格式

所有接口都使用下面的外层结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

`data` 里面才是具体业务数据。前端只需按一种规则解析响应，不必为每个接口单独猜测格式。

### 5. 环境变量与密钥管理

`.env.example` 是配置模板，真实 `.env` 不进入 Git。JWT 密钥、数据库地址、模型 API Key 等都从环境变量读取，避免把秘密写死在代码里。

### 6. 依赖锁定

`pyproject.toml` 记录直接依赖，`requirements.lock.txt` 记录本次安装得到的完整版本。锁定版本能减少「昨天能运行，升级后突然坏了」的问题。

### 7. Ruff、Pytest 与 Git

- Ruff：检查代码规范、错误和格式。
- Pytest：自动运行测试，防止修改新功能时破坏旧功能。
- Git：按小任务保存历史，每一步都能查看改了什么，也能回退。

## 目录为什么这样安排

`backend/app/core/` 放所有模块共用的能力，例如配置、异常、日志；`backend/app/modules/` 按业务模块放代码。后续生活管家、食材管家等互不混在一起。

`frontend/src/api/` 将统一存放后端请求，`views/` 放页面，`stores/` 放少量全局状态，`types/` 放与后端对应的数据类型。

## 如何运行和验证

```bash
# 后端，在 backend 目录执行
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
.venv/Scripts/python.exe -m pytest

# 前端，在 frontend 目录执行
npm run dev
npm run build
```

健康检查地址：`http://localhost:8000/api/v1/health`。前端开发地址通常是 `http://localhost:5173`。

## 本阶段验收结果

- Ruff 检查与格式检查通过。
- 后端健康检查测试通过。
- 实际启动 Uvicorn 后，健康检查返回正确 JSON，Swagger 页面可访问。
- 前端生产构建通过。

## 常见问题

**为什么不一开始就把所有功能写完？** 因为功能越多，问题越难定位。先让最小工程稳定运行，再逐步增加功能，每次只需要检查一小段改动。

**为什么健康检查不需要登录？** 它只返回服务是否运行等最基本信息，用于部署和故障排查，不暴露用户数据。
