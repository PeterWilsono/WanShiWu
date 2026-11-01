# 阶段 11.2：修复桌面软件再次打开失败

## 用户反馈与日志

1.0.0 首次安装后可以打开，再次启动出现错误。用户提供的 `backend.log` 只有 Alembic 成功与 Uvicorn 监听 `127.0.0.1:8765` 的记录，没有数据库异常，说明不能只根据弹窗判断后端启动失败。

## 复现与根因

使用现有数据目录运行 1.0.0，复现 `ERR_FAILED (-2) loading http://127.0.0.1:8765/`，随后确认有两个叠加因素：

1. 当前环境存在 HTTP 代理，桌面 Chromium 将本机回环地址也交给代理，后端健康但窗口无法加载。
2. 首次运行注册的 PWA Service Worker 留存在原桌面配置中。仅增加代理绕过后，全新桌面配置成功、旧配置仍失败，证明旧离线缓存也参与拦截。

## 修复

- Electron 启动参数增加 `no-proxy-server`，应用窗口对本机服务始终直连；外部 AI 请求仍由后端处理。
- 每次加载本机页面前，仅清理该 origin 的 `serviceworkers` 和 `cachestorage`，不清理 `localStorage` 登录态，更不触碰 SQLite 业务数据。
- 前端通过 Electron UserAgent 识别桌面环境，桌面版不再注册 PWA；普通浏览器继续保留 PWA。
- 桌面版本升级为 1.0.1，旧版本可直接覆盖安装。

## 验证

- 修复前在原配置和代理环境下稳定复现 `ERR_FAILED`。
- 修复后使用相同原配置、相同代理和现有数据目录，连续两次启动均输出 `WANSHIWU_DESKTOP_SMOKE_OK`。
- 1.0.1 覆盖安装到原 1.0.0 测试目录后，再次连续启动两次均成功。
- 后端全量 341 项测试通过，Ruff、Electron 主进程语法和前端 TypeScript/Vite/PWA 构建通过。
- 未删除或重建用户数据库；缓存清理不包含登录 localStorage。

最终安装包：`desktop/release/v1.0.1/万事屋-Windows-1.0.1-安装包.exe`。
