# 阶段 9.1：MiMo / DeepSeek 模型配置后端

## 这一阶段解决什么

过去所有 AI 请求都读取同一个 `.env`，页面无法配置，也无法同时保留两家服务。本阶段增加按用户隔离的模型配置，让 MiMo 和 DeepSeek 可以分别保存、自由切换。

## 官方接入参数

- 小米 MiMo：OpenAI 兼容地址 `https://api.xiaomimimo.com/v1`，默认模型 `mimo-v2.6-pro`；也支持官方 Token Plan 地址。
- DeepSeek：OpenAI 兼容地址 `https://api.deepseek.com`，默认模型 `deepseek-flash`。
- 模型名和 Base URL 可在设置中修改，但接口地址仅允许对应服务商的官方 HTTPS 域名，避免密钥被发送到任意地址。

## 实现内容

- 新增 `user_llm_configs` 表，按 `(user_id, provider)` 唯一保存两组配置。
- API Key 使用 Fernet 加密后保存，密钥材料由服务端 JWT 密钥派生；接口只返回末四位掩码。
- 新增 `GET/PUT /settings`、`PUT/DELETE /settings/llm/{provider}` 和 `POST /settings/llm/{provider}/test`。
- 连接测试区分无效密钥、地址/模型不存在、额度/限流、超时与服务异常，不返回原始服务端响应。
- 统一 `LLMClient` 每次按当前用户解析模型；未配置时明确引导到“我的 → 设置”。后台收藏摘要与周报也因此自动使用同一套用户配置。
- 通用设置支持 IANA 时区、食材临期天数和每日 AI 调用上限。

## 安全边界

- 密钥不会进入前端响应、日志或 LLM 审计内容。
- 修改 `JWT_SECRET` 后，已加密密钥无法解密，需要重新填写；生产环境必须固定并妥善保管该服务端密钥。
- 本地开发仍可用 `.env` 中的 DeepSeek 配置兜底，用户保存的配置优先。

## 验证

- 新增 9 项设置测试，与 LLM 客户端合计 15 项测试通过。
- Ruff 检查通过。
- 开发数据库已升级到 `a41c0e72b9d6`。
- 连接测试使用模拟 SDK，未访问真实 MiMo / DeepSeek，也未消耗真实额度；真实 Key 需要用户在页面上自行测试。
