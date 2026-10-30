# 阶段 2.5：前端待办 API 封装与 TypeScript 类型

## 这一步在做什么

前面后端已经提供完整的待办接口，但前端页面还不应该直接在每个组件里写 URL 和 Axios 请求。本阶段增加两层基础设施：

- `frontend/src/types/todo.ts`：描述待办数据、请求参数和响应结构；
- `frontend/src/api/todos.ts`：集中封装六个待办接口。

下一步开发列表页和编辑表单时，组件只需要调用函数并处理返回的数据。

## 封装的接口

| 前端函数 | 后端接口 | 用途 |
| --- | --- | --- |
| `listTodos(params)` | `GET /todos` | 分页、筛选和排序 |
| `createTodo(data)` | `POST /todos` | 新建待办 |
| `getTodo(id)` | `GET /todos/{id}` | 获取单条详情 |
| `updateTodo(id, data)` | `PATCH /todos/{id}` | 局部修改 |
| `deleteTodo(id)` | `DELETE /todos/{id}` | 软删除 |
| `completeTodo(id)` | `POST /todos/{id}/complete` | 完成并获取可能的下一次待办 |

## 需要理解的知识

### 1. 为什么类型文件和 API 文件要分开

类型描述“数据长什么样”，API 函数描述“如何获取或修改数据”。分开后：

- 组件可以只导入类型，不必加载请求代码；
- 多个 API 模块可以复用同一批类型；
- 后端字段变化时，有明确的同步位置。

这与后端 schemas 和 service 分层的思路相似。

### 2. TypeScript 联合类型有什么用

状态和周期不是任意字符串，而是有限选项：

```ts
type TodoStatus = 'pending' | 'done' | 'cancelled'
type Recurrence = 'none' | 'daily' | 'weekly' | 'monthly'
```

如果代码误写成 `'finished'`，TypeScript 会在构建前报错，而不是等请求发到后端才返回 422。

优先级也定义为 `1 | 2 | 3`，避免把无效数字传给后端。

### 3. 可选字段与 null 的区别

在 `TodoUpdateRequest` 中：

```ts
note?: string | null
```

- 不写 `note`：PATCH 不修改备注；
- `note: null`：明确清空备注；
- `note: '新备注'`：修改备注。

这与阶段 2.3 后端使用 `exclude_unset` 的规则一一对应。

### 4. 为什么日期使用 string

JSON 没有独立的日期类型，后端把 datetime 序列化为 ISO 8601 字符串。因此 TypeScript 中使用 `string`，例如：

```text
2026-11-01T15:30:00Z
```

API 层不擅自转换为 `Date`，避免在不同页面重复转换或丢失时区。后续展示层再根据用户时区格式化。

### 5. 统一响应在哪里被拆开

后端实际返回：

```json
{ "code": 0, "message": "ok", "data": {} }
```

`api/todos.ts` 使用 `ApiResponse<T>` 描述完整结构，但只把 `response.data.data` 返回给页面。因此组件拿到的是直接的 `Todo` 或 `TodoListResponse`，不需要每个页面重复判断 `code`。

请求 Token、401 清理与跳转、网络错误和业务错误转换，仍由已有的 `api/http.ts` 拦截器处理，没有重复实现。

## 使用示例

```ts
import { completeTodo, listTodos, updateTodo } from '../api/todos'

const result = await listTodos({
  status: 'pending',
  tag: '工作',
  page: 1,
  page_size: 20,
  sort: 'due_at',
  order: 'asc',
})

await updateTodo(1, { priority: 3 })
const { todo, next_todo } = await completeTodo(1)
```

失败时捕获统一的 `ApiError`，而不是读取 Axios 的内部响应结构。

## 如何验证

```bash
cd frontend
npm run build
```

构建命令先运行 `vue-tsc` 类型检查，再运行 Vite 生产构建。本阶段两项均通过。当前仍有 Element Plus 全量引入造成的包体积提示，不影响功能，后续再做按需加载优化。

本阶段没有引入前端测试框架，因此验证范围是类型检查与构建；实际页面联调将在下一阶段进行。

## 下一步

阶段 2.6 将实现待办页面：列表、筛选、新建、编辑、完成、删除，以及周期任务完成后的新记录展示。
