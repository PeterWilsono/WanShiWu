# 阶段 4 收尾：PWA 安装配置与离线提示

## 这一步做什么

让万事屋具备 PWA 基础能力：浏览器可以识别应用名称、图标、主题色和独立窗口显示方式，并通过 Service Worker 缓存应用外壳。网络断开时，页面底部会显示友好提示。

本任务遵循说明书的明确边界：**支持添加到主屏幕，但不承诺离线业务功能可用**。

## PWA 的几个概念

- **Web App Manifest**：告诉浏览器应用叫什么、使用什么图标、从哪个地址启动、以浏览器标签页还是独立窗口打开。
- **Service Worker**：浏览器在后台运行的脚本，可以缓存静态文件。本项目使用 vite-plugin-pwa 自动生成，没有手写复杂的缓存策略。
- **应用外壳**：HTML、JS、CSS、图标等界面文件。预缓存它们可以让已安装的界面更快打开。
- **业务 API**：待办、账目、通知等实时数据。本任务不缓存这些响应，避免断网后把旧数据误认为最新数据。

## 具体实现

`vite.config.ts` 注册 VitePWA：

- 名称“万事屋 · 个人生活效率平台”，短名称“万事屋”，语言 `zh-CN`。
- 主题色 `#409eff`，`display=standalone`，启动地址和作用域均为 `/`。
- 使用项目自己的 `pwa-icon.svg`，声明 `any` 与 `maskable` 两种用途。
- 使用 `generateSW` 和 `autoUpdate`，新版本发布后自动更新 Service Worker。
- 导航回退到 `/index.html`，但 `/api/` 路径明确排除；没有添加业务 API 的 runtime cache。

`main.ts` 通过 `virtual:pwa-register` 注册 Service Worker；`tsconfig.app.json` 加入对应类型。

`NetworkStatus.vue` 监听浏览器 `online` / `offline` 事件。断网时提示：“已打开的内容可继续查看，但保存、同步和 AI 功能需要联网。”组件卸载时移除监听，避免重复绑定。

## 改动文件

- `frontend/package.json`、`package-lock.json`：新增开发依赖 vite-plugin-pwa。
- `frontend/vite.config.ts`：Manifest 与 Workbox 配置。
- `frontend/public/pwa-icon.svg`：可缩放应用图标。
- `frontend/index.html`：主题色、描述和图标入口。
- `frontend/src/main.ts`、`tsconfig.app.json`：Service Worker 注册与类型。
- `frontend/src/components/NetworkStatus.vue`、`App.vue`：全局网络状态提示。

依赖与 npm 缓存均放在 D 盘项目内，没有向 C 盘下载依赖。

## 如何验证

```bash
npm --prefix frontend run build
```

`vue-tsc`、Vite 与 PWA 生成全部通过。构建产物包含：

- `dist/manifest.webmanifest`
- `dist/sw.js`
- `dist/workbox-*.js`
- 27 个预缓存条目

Manifest 中的中文名称、语言、主题色、图标与启动范围已检查。构建仍有项目整体的包体积提示，没有 PWA 相关错误。

## 尚需人工验收与边界

PWA 安装通常要求 HTTPS，localhost 开发环境除外。手机“添加到主屏幕”、独立窗口、断网提示和更新流程，仍需要在部署或局域网 HTTPS 环境中用真实浏览器验收；本次没有伪称已完成设备测试。

当前使用 SVG 图标，不同系统的 PWA 图标兼容性可能不同；若目标设备要求 PNG，可在交付阶段补 192/512 PNG 后备图标。业务数据不在离线缓存范围内，离线时不保证列表和保存功能可用。
