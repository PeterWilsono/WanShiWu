# 阶段 2.22：日程与待办月历视图

## 这一步做什么

新增 `/calendar` 月历页面，在同一张日历里显示：

- 蓝色：日程，包括跨开始、结束时间的日程。
- 橙色：有截止时间的待办；已完成和已取消的待办会弱化显示。
- 点击任意条目：弹出标题、时间、地点、状态、优先级、备注等详情，并可跳转到对应管理页。

月历支持上一月、下一月、今天和单日条目过多时的“更多”弹层。首页和日程管理页增加了入口，小屏幕下工具栏允许换行。

## 数据如何加载

FullCalendar 每次切换可见月份时会给出视图日期范围。页面并行调用：

- `GET /events?range_start=...&range_end=...`：返回与窗口重叠的日程。
- `GET /todos?due_after=...&due_before=...`：返回窗口内有截止时间的待办。

FullCalendar 的 `end` 是开区间，现有后端 `range_end` / `due_before` 是含边界查询，因此请求前将结束时间减 1 毫秒，避免把下一段视图起点的数据重复算进来。

接口单页最多 100 条。个人使用通常足够，但如果当前六周视图中的日程或待办超过已加载数量，页面会显示警告并指引到管理页分页查看，不会假装已经加载完整。

## 时间与状态处理

数据库和 API 时间仍保持带时区的 ISO 字符串。日历使用当前用户的 IANA 时区（例如 Asia/Shanghai）展示；详情弹窗继续复用 `formatDateTime()`，不在页面里另写一套 UTC 换算逻辑。

日历条目 ID 加上 `event-` 或 `todo-` 前缀，避免不同表里的相同数字主键冲突。原始类型和详情放在 `extendedProps`，点击时无需再发请求。

## 改动文件

- `frontend/package.json`、`frontend/package-lock.json`：安装 FullCalendar core、daygrid、interaction、vue3。
- `frontend/src/views/CalendarView.vue`：月历、两类数据转换、加载状态和详情弹窗。
- `frontend/src/router/index.ts`：注册需要登录的 `/calendar` 路由。
- `frontend/src/views/HomeView.vue`、`EventView.vue`：增加月历入口。

依赖与 npm 缓存均放在 D 盘项目内。初次安装时 Vue 适配包与其他包主版本不同，导致类型冲突；最终四个 FullCalendar 包统一锁定为 **6.1.22**，依赖树只有一份 core。

## 如何验证

```bash
npm --prefix frontend ls @fullcalendar/core @fullcalendar/vue3 @fullcalendar/daygrid @fullcalendar/interaction
npm --prefix frontend run build
```

版本检查确认四个包均为 6.1.22 且 core 正确去重。`vue-tsc` 和 Vite 生产构建通过；构建仍有项目整体的包体积提示，没有月历相关错误。

## 当前边界

本任务是只读月历：不支持在日历中拖拽改期或直接新建，修改仍进入现有待办/日程管理页完成，避免绕过原表单校验和提醒事务联动。当前未添加浏览器 E2E，因此不宣称已自动覆盖全部浏览器交互。
