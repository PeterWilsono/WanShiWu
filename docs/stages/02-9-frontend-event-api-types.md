# 阶段 2.9：前端日程 API 封装与 TypeScript 类型

## 这一步在做什么

后端已经提供日程的新建、列表、详情、局部修改和软删除接口。本阶段在前端建立对应的类型与调用函数，为下一阶段日程页面做准备。

新增两个文件：

- `frontend/src/types/event.ts`：描述日程数据和各种请求、响应的结构；
- `frontend/src/api/events.ts`：集中封装五个日程 API 调用。

这一步没有新增页面，也没有改变后端行为。

## 需要理解的知识

### 1. 为什么前端也要定义一套类型

后端 Pydantic 会在服务端检查数据，但 TypeScript 编写页面时无法自动知道 Python Schema 的内容。如果每个页面都随意写 `{ id, title }`，容易出现：

- 把 `start_at` 错写成 `startAt`；
- 忘记 `end_at` 可能为 `null`；
- 把提醒分钟当成必填字段；
- 误以为 PATCH 必须提交完整日程。

`Event`、`EventCreateRequest` 和 `EventUpdateRequest` 等接口把后端契约明确映射到前端。字段名或可空性写错时，`vue-tsc` 会在构建阶段直接报错，而不是等用户点击页面后才发现。

这些类型需要手动与后端保持同步，并不意味着 TypeScript 能在浏览器里验证服务器实际返回的 JSON；运行时校验仍由后端和接口测试负责。

### 2. 为什么时间使用 string 而不是 Date

API 中的时间是 ISO 8601 字符串，例如：

```text
2026-11-10T01:00:00Z
```

类型层保持 `string`，避免 API 封装隐式创建 `Date`、隐式转换时区。页面展示或表单编辑时，再根据当前用户时区明确转换。

`Event.end_at` 和 `Event.remind_before_min` 等字段使用 `string | null`、`number | null`，提醒页面必须处理“未设置”的情况。

### 3. 创建与修改为什么使用不同入参

`EventCreateRequest` 中：

- `title` 和 `start_at` 必填；
- 其他字段可以省略；
- `end_at` 等可空字段也可以显式传 `null`。

`EventUpdateRequest` 中所有字段都可省略，因为 PATCH 只修改明确提交的内容：

```ts
await updateEvent(1, { location: '5 号会议室' })
```

只修改地点，其他字段保持不变。

```ts
await updateEvent(1, { end_at: null, note: null })
```

显式清空结束时间和备注。

`start_at` 在修改类型中是 `string | undefined`，不允许传 `null`，与后端“开始时间不能清空”的规则一致。

### 4. 列表参数为什么叫 range_start / range_end

日程列表不是简单查询“开始时间落在窗口内”的记录，而是查询与窗口重叠的记录：

```ts
const result = await listEvents({
  range_start: '2026-11-10T00:00:00+08:00',
  range_end: '2026-11-11T00:00:00+08:00',
  page: 1,
  page_size: 50,
})
```

类型命名与后端一致，避免页面把它误解为只筛选 `start_at`。跨窗口的多天日程也能正确返回。

### 5. API 封装层负责什么

`events.ts` 负责 URL、HTTP 方法和统一响应拆包。例如：

```ts
const response = await http.get<ApiResponse<EventListResponse>>('/events', { params })
return response.data.data
```

页面直接得到 `EventListResponse`，不需要了解 AxiosResponse 或 `{ code, message, data }` 外壳。

以下横切能力继续由现有 `http.ts` 统一处理，不在每个函数中重复：

- 自动携带 Bearer Token；
- 401 清理登录状态并跳转登录页；
- 网络与业务错误转换为 `ApiError`；
- 统一 API 基础路径与超时。

## 提供的五个函数

| 函数 | 后端接口 | 返回值 |
| --- | --- | --- |
| `listEvents(params)` | `GET /api/v1/events` | 分页日程列表 |
| `createEvent(data)` | `POST /api/v1/events` | 新建后的日程 |
| `getEvent(id)` | `GET /api/v1/events/{id}` | 日程详情 |
| `updateEvent(id, data)` | `PATCH /api/v1/events/{id}` | 修改后的日程 |
| `deleteEvent(id)` | `DELETE /api/v1/events/{id}` | `Promise<void>` |

使用示例：

```ts
import { createEvent, listEvents } from '../api/events'

await createEvent({
  title: '牙医复诊',
  start_at: '2026-11-10T09:00:00+08:00',
  remind_before_min: 30,
})

const events = await listEvents({ page: 1, page_size: 50 })
```

## 如何验证

```bash
cd frontend
npm run build
```

该命令先执行 `vue-tsc -b` 类型检查，再执行 Vite 生产构建。本阶段两者均通过，未安装新依赖。构建仍有既有的 Element Plus 主包体积提示，不影响功能，留待后续性能优化。

本阶段没有引入前端单元测试或浏览器 E2E，因此这里只声明类型与构建验证通过，没有宣称页面联调已完成。

## 下一步

阶段 2.10 将实现日程页面：按时间范围加载、新建与编辑表单、详情操作和删除确认，并复用本阶段的类型与 API。
