# 阶段 2.21：前端月度统计与 ECharts 图表

## 这一步做什么

新增 `/stats` 月度统计页面，把阶段 2.20 的两个接口变成可以直接阅读的图表：

- 月份选择器：切换自然月后重新请求数据。
- 收支总览：收入、支出、结余三张卡片，金额统一通过 `formatMoney()` 从分格式化为元。
- 支出分类占比：环形饼图，只统计 expense 类型，不把收入混入支出占比。
- 每日支出：折线图展示月初到月末，后端补零的日期会落在零线上。

首页和记账页都增加了“月度统计”入口。页面包含请求加载状态、失败提示与重试按钮、无支出时的空状态；窄屏下汇总卡片改为单列，两个图表改为上下排列。

## 为什么使用 ECharts

饼图和折线图不仅是画几条线，还涉及坐标轴、提示框、图例、缩放和无障碍说明。说明书已选定 ECharts，因此按用户确认安装到 D 盘项目的 `frontend/node_modules`，没有向 C 盘下载依赖，npm 缓存也放在项目的 node_modules 内。

`EChart.vue` 是轻量公共组件，只负责：

1. 挂载时创建图表并传入配置。
2. 配置变化时替换图表内容。
3. 使用 ResizeObserver 在容器宽度变化时调用 `resize()`。
4. 组件卸载时断开观察并销毁图表，避免残留引用。

这里按需注册折线图、饼图、坐标轴、提示框、图例和 Canvas 渲染器，而不是在应用入口注册全部图表。

## 改动文件

- `frontend/package.json`、`frontend/package-lock.json`：新增 ECharts 依赖。
- `frontend/src/types/stats.ts`：与后端统计响应对应的 TypeScript 类型。
- `frontend/src/api/stats.ts`：月度和每日统计请求。
- `frontend/src/components/EChart.vue`：可缩放、可销毁的通用图表容器。
- `frontend/src/views/StatsView.vue`：统计页、卡片和图表配置。
- `frontend/src/router/index.ts`：注册需要登录的 `/stats` 路由。
- `frontend/src/views/HomeView.vue`、`TransactionView.vue`：增加页面入口。

## 如何验证

```bash
npm --prefix frontend run build
```

该命令先执行 `vue-tsc -b` 类型检查，再执行 Vite 生产构建，本次均已通过。统计页通过路由动态导入单独分包；构建输出仍有包体积提示，但没有类型或构建错误。

当前项目尚无前端组件测试或浏览器 E2E，因此这里不宣称已经自动验证每一种浏览器尺寸和鼠标交互。

## 当前边界

本任务只展示统计，不支持点击饼图筛选账目，也不包含月预算、超支预警或 CSV 导出。
