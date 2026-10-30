# 阶段 1.4：前端 Axios 封装与 Pinia 登录状态

## 这一阶段在做什么

阶段 1.3 已经有后端注册、登录和 me 接口，但浏览器还没有统一的调用方式。本阶段搭建前端认证基础设施：

- 所有请求使用统一的 Axios 实例和 `/api/v1` 基础地址。
- 请求自动携带 `Authorization: Bearer <token>`。
- 后端业务错误统一转换成 `ApiError`。
- Token 持久化到 localStorage，刷新页面后仍然保留。
- Pinia 保存 Token、当前用户和登录加载状态。
- 普通接口收到 401 时清除 Token，并跳转到登录页。

本阶段不做登录页面和路由守卫，它们在下一小任务接入。

## 主要文件

- `frontend/src/api/http.ts`：Axios 实例、请求/响应拦截器、统一 `ApiError`、401 处理。
- `frontend/src/api/auth.ts`：注册、登录、获取当前用户三个 API 函数。
- `frontend/src/stores/auth.ts`：Pinia 认证状态和登录、注册、退出、获取用户操作。
- `frontend/src/utils/authStorage.ts`：Token 在 localStorage 中的唯一读写入口。
- `frontend/src/types/api.ts`：与后端统一响应对应的 TypeScript 类型。
- `frontend/src/types/auth.ts`：与后端认证 Schema 对应的请求、用户和令牌类型。

## 用到的主要知识

### 1. 为什么页面不能直接使用 Axios

如果每个页面都自己写 baseURL、请求头和错误解析，很快会出现重复代码和不一致行为。例如某个页面忘记带 Token，另一个页面把 401 当普通提示显示而没有退出登录。

本项目规定所有后端请求只写在 `src/api/`。页面和 Pinia 调用语义明确的函数，例如 `authApi.login()`，不关心 HTTP 细节。

### 2. Axios 实例与 baseURL

`http` 是统一创建的 Axios 实例：

- 默认 baseURL 是 `/api/v1`；调用时只需写 `/auth/login`。
- 默认超时 10 秒，避免网络异常时请求一直等待。
- 开发环境中，Vite 把 `/api` 代理到 `localhost:8000`，所以浏览器不需要处理跨域。
- 部署时可通过 `VITE_API_BASE_URL` 改地址，不必修改业务代码。

### 3. 请求拦截器

请求拦截器在每次请求发出前执行。它从 localStorage 读取 Token，存在时写入：

```http
Authorization: Bearer <token>
```

这样新增业务 API 时不需要重复写认证请求头，也不容易遗漏。

### 4. 响应拦截器与 ApiError

后端错误外层格式是 `code / message / data`，网络错误和 Axios 自身错误则不是这种结构。响应拦截器把它们统一转换为 `ApiError`，页面只需要读取：

- `message`：给用户看的提示；
- `code`：项目业务错误码；
- `status`：HTTP 状态码，网络未连接时可能不存在；
- `data`：参数错误详情等附加数据。

HTTP 200 但业务码非 0 的情况也会按失败处理，不能只根据 HTTP 状态判断业务是否成功。

### 5. 为什么登录接口的 401 不能自动跳转

普通接口返回 401，通常表示 Token 失效，需要重新登录。但登录接口返回 401 往往只是「用户名或密码错误」，应该留在登录页显示提示。

因此拦截器对 `/auth/login` 做了例外处理，不会在密码输错时刷新页面或清除用户刚输入的内容。

### 6. localStorage 与 Pinia 的区别

- localStorage 是浏览器持久存储，刷新或重新打开页面后数据仍在。
- Pinia 是应用运行期间的响应式内存状态，数据变化会自动驱动 Vue 页面更新。

Token 需要两者配合：localStorage 负责持久化，Pinia 的 `token` 和 `user` 负责让页面实时知道登录状态。退出登录时两者都要清理。

localStorage 中的 Token 可以被本页 JavaScript 读取，所以后续必须注意 XSS 防护，不渲染未经处理的 HTML，也不能把第三方敏感脚本随意引入页面。

### 7. Pinia Setup Store

`auth.ts` 使用 Setup Store 写法：`ref` 定义状态，`computed` 定义派生状态，函数定义操作。

- `token`：当前访问令牌；
- `user`：后端确认过的当前用户；
- `loading`：登录请求是否进行中，登录页可用它禁用按钮、防止重复提交；
- `isAuthenticated`：由 Token 是否存在计算得到，不单独保存一份，避免两个状态不一致。

Pinia 只保存全局认证信息。未来待办列表、账单列表等仍留在各自页面，不全部塞进全局 store。

### 8. 登录为什么成功拿到 Token 后还要请求 me

登录响应只证明凭据正确并给出 Token，不包含完整用户信息。store 接着请求 `/auth/me`，确认 Token 可用并取得用户名、时区和设置。

如果第二步失败，会清理 Token 和用户状态，避免出现「界面显示已登录，但令牌实际不可用」的假登录状态。

### 9. 为什么单独抽出 authStorage

如果 `http.ts` 直接导入 auth store，而 auth store 又通过 `auth.ts` 导入 `http.ts`，就会形成循环依赖。独立的 `authStorage.ts` 只负责 Token 存取，双方都可以依赖它，结构更稳定。

## 登录流程

```text
用户提交账号密码（下一阶段登录页）
  → auth store 调用 /auth/login
  → 成功后保存 Token 到 localStorage + Pinia
  → 自动调用 /auth/me
  → Axios 请求拦截器自动携带 Token
  → 后端返回当前用户
  → Pinia 保存 user，页面获得响应式登录状态
```

普通接口收到 401 时：

```text
清除 localStorage 中的 Token
  → 跳转 /login?redirect=原页面地址
  → 页面刷新后 Pinia 重新从未知状态初始化
```

`redirect` 参数会在登录页和路由守卫阶段使用，让登录成功后返回原目标页面。

## 后续页面怎样使用

```ts
const authStore = useAuthStore()

try {
  await authStore.login({ username, password })
  // 登录成功，authStore.user 已有当前用户
} catch (error) {
  if (error instanceof ApiError) {
    // 使用 error.message 显示统一错误提示
  }
}
```

页面不直接读 localStorage，也不直接调用 Axios。

## 如何验证

```bash
cd frontend
npm run build
```

`npm run build` 会先执行 `vue-tsc -b` 做 TypeScript / Vue 类型检查，再执行 Vite 生产构建。本阶段两项均已通过。

构建会提示主 JS 包超过 500 kB，主要因为当前全量引入 Element Plus；这是体积优化提示，不是构建失败。后续可通过按需引入和路由分包优化，不影响本阶段功能。

## 当前边界与下一步

现在已有认证 API 和状态管理，但还没有用户可操作的登录页，也还没有 `/login` 路由和守卫。下一小任务将完成这些界面与导航逻辑，并把登录成功后的回跳串起来。
