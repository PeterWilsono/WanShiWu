# 阶段 1.3：注册、登录与 JWT 鉴权

## 这一阶段在做什么

这一阶段让后端真正认识「当前用户是谁」：

1. 用户通过 `/api/v1/auth/register` 创建账号。
2. 用户通过 `/api/v1/auth/login` 登录，获得访问令牌 `access_token`。
3. 后续请求在请求头中携带令牌，后端验证后才知道当前用户。
4. `/api/v1/auth/me` 返回当前用户资料，是验证鉴权是否工作的第一个受保护接口。

后续待办、账目、食材等数据都带 `user_id`，它们都会复用这里实现的 `get_current_user`，确保用户只能操作自己的数据。

## 主要文件

- `backend/app/core/security.py`：Argon2 密码哈希、密码校验、JWT 签发与解码。
- `backend/app/modules/auth/schemas.py`：注册、登录、用户信息和令牌的数据结构及参数校验。
- `backend/app/modules/auth/service.py`：创建用户、检查用户名、验证登录凭据。
- `backend/app/modules/auth/dependencies.py`：`get_current_user`，从 Bearer 令牌找出当前用户。
- `backend/app/modules/auth/router.py`：注册、登录、me 三个 HTTP 接口。
- `backend/app/main.py`：把认证路由挂载到 `/api/v1`。
- `backend/tests/test_auth_api.py`：正常流程和各类失败场景的接口测试。
- `backend/tests/conftest.py`：新增使用独立内存数据库的接口测试客户端。

## 用到的主要知识

### 1. 为什么不能保存原始密码

如果数据库保存原始密码，一旦数据库泄露，所有密码都会直接暴露。用户还可能在其他网站使用相同密码，损失会进一步扩大。

因此数据库只保存 `password_hash`。登录时不是「解密数据库里的密码」，而是把用户刚输入的密码交给 Argon2 校验。

### 2. Argon2、哈希与随机盐

哈希是单向计算，不能还原出原密码。Argon2 专门用于密码哈希，计算成本可调，比简单计算一次 SHA-256 更适合抵抗密码破解。

随机盐意味着：即使两个人使用完全相同的密码，数据库里的哈希也不一样。攻击者不能用一张预先算好的通用表直接批量匹配。

当前测试还明确检查：接口响应不包含 `password` 或 `password_hash`，数据库中的哈希也不等于原始密码。

### 3. JWT 是什么

JWT（JSON Web Token）是一种带签名的访问令牌。本项目的令牌包含：

- `sub`：用户 ID；
- `iat`：签发时间；
- `exp`：过期时间。

后端使用 `HS256` 和 `JWT_SECRET` 签名。令牌内容可以被读取，但在不知道密钥的情况下不能合法篡改；如果修改用户 ID 或过期时间，签名校验就会失败。

JWT 不是加密容器，所以不把密码、密码哈希或其他敏感资料放进去。

### 4. 为什么登录后每次请求还要带令牌

HTTP 本身无状态，第二个请求不会自动记得第一个请求已经登录。前端登录后保存令牌，之后发送：

```http
Authorization: Bearer <access_token>
```

`get_current_user` 会验证令牌格式、签名、有效期和用户是否仍然存在，再查询数据库并返回 `User` 对象。

### 5. 依赖注入怎样复用鉴权

FastAPI 的依赖可以理解为「路由执行前需要的公共资源」。`get_db` 提供数据库会话，`get_current_user` 提供当前用户。

以后受保护接口只需声明 `current_user: CurrentUser`，不必在每个路由重复解析令牌。测试也能替换 `get_db`，让接口测试完全不碰真实数据库。

### 6. 路由、service、schema 分别负责什么

- Schema：请求和响应长什么样，字段是否合法。
- Router：接收 HTTP 请求，调用业务逻辑，组装统一响应。
- Service：执行注册和登录规则，不关注 HTTP 细节。
- Model：数据库里的用户记录。

这种分层让业务规则可以独立测试，也避免把所有代码堆进一个路由函数。

### 7. 为什么登录失败不区分「用户不存在」和「密码错误」

两种失败都返回 40102 和「用户名或密码错误」。如果明确告诉访问者用户名存在，只是在密码上失败，就会泄露账号信息，方便定向尝试。

### 8. 为什么已有查询检查，还要数据库唯一约束

注册前查询用户名可以提供友好提示，但两个几乎同时到来的请求可能都查到「不存在」。数据库唯一约束是最后防线。提交时捕获 `IntegrityError`，回滚事务并返回 40901，避免脏数据或未完成事务。

### 9. 关闭公开注册

设置 `ALLOW_REGISTER=false` 后，注册接口返回 404。登录和已有账号的 me 接口不受影响。这符合单用户场景：初始化账号后可以关闭新注册。

## 接口调用示例

### 注册

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "peter",
  "password": "correct-horse-123"
}
```

成功时 `code=0`，`data` 中包含用户 ID、用户名、时区、设置和创建时间，不包含密码信息。重复用户名返回 HTTP 409 / 业务码 40901。

### 登录

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "peter",
  "password": "correct-horse-123"
}
```

成功时：

```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "access_token": "<JWT>",
    "token_type": "bearer"
  }
}
```

### 获取当前用户

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

未携带令牌、令牌无效、令牌过期或令牌指向的用户不存在，都返回 HTTP 401 / 业务码 40101。

## 如何自己验证

启动后端：

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

打开 `http://localhost:8000/docs`，依次尝试 `/api/v1/auth/register` 和 `/api/v1/auth/login`。复制登录返回的 `access_token`，点击 Swagger 中 `/auth/me` 接口的认证入口或直接在请求头中使用 `Bearer <token>`，再请求 `/api/v1/auth/me`。

注意：Swagger 的 Bearer 输入框通常只填令牌本身，不重复输入 `Bearer ` 前缀。

## 自动化验证结果

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -v
```

本阶段完成后，项目共 19 个测试全部通过。认证测试覆盖：

- 注册 → 登录 → me 的完整正常流程；
- 数据库只保存密码哈希，响应不泄露密码字段；
- 重复用户名、参数过短、错误凭据；
- 无令牌、无效令牌、过期令牌、用户不存在的令牌；
- 环境变量关闭注册。

## 当前边界与下一步

这一阶段只完成后端认证 API，还没有前端登录页、token 持久化和路由守卫。下一步将在前端实现 axios 封装与登录状态，让浏览器真正串起这套流程。
