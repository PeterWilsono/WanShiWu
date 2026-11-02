# 阶段 12.1：GitHub 公开发布与安装包下载

## 目标

将万事屋整理为其他人可以阅读、克隆和直接下载安装的公开项目，同时避免上传个人数据、密钥、依赖和临时构建文件。

## 发布前审查

用户新增内容主要集中在 README、MIT 许可证和 GitHub 指南，没有业务代码改动。修正了 GitHub 用户名占位符、过时的仓库名、本机安装包路径、过宽的“离线可用”表述和不准确的完成度说明。

原 README 改名并整理为 `DEVELOPMENT.md`，新 README 面向普通使用者。保留 MIT 许可证和“云程”署名，关联 GitHub 账号 `PeterWilsono`，不公开额外联系邮箱。

## 文件边界

- 上传：源码、测试、文档、桌面打包配置、CI 配置和 MIT 许可证。
- 不上传：`.env`、数据库、模型 Key、虚拟环境、`node_modules`、缓存、日志、测试安装目录。
- 安装包约 160 MB，通过 GitHub Release 分发，不进入 Git 源码历史。
- `.tools/` 保存本地发布工具和授权配置，已加入 `.gitignore`，不会上传。

## 公开地址

- 仓库：<https://github.com/PeterWilsono/WanShiWu>
- v1.0.2 Release：<https://github.com/PeterWilsono/WanShiWu/releases/tag/v1.0.2>
- 最新版安装包：<https://github.com/PeterWilsono/WanShiWu/releases/latest/download/WanShiWu-Setup.exe>

## 授权问题与解决

GitHub 连接器可以读取当前账号，但创建仓库返回 403，说明授权范围不足。改用 GitHub 官方 CLI 的浏览器设备授权，并将工具及配置放在项目 `.tools/` 中。

第一次源码推送被 GitHub 拒绝，因为历史包含 `.github/workflows/ci.yml`，OAuth App 必须具有额外 `workflow` 权限。补充该权限后推送成功，没有删除或绕过 CI 配置。

## 验证

- 仓库为 PUBLIC，默认分支为 `main`，远程源码与本地提交一致。
- GitHub Actions 首次运行 `41372703484`：backend 与 frontend 均为 success。
- 后端在干净 CI 环境完成依赖安装、Ruff、pytest 和 80% 覆盖率门槛。
- 前端在干净 CI 环境完成 `npm ci` 和生产构建。
- Release `v1.0.2` 非草稿、非预发布，附件 `WanShiWu-Setup.exe` 状态为 uploaded，大小 167111494 字节。
- 从公开 `releases/latest/download/WanShiWu-Setup.exe` 地址重新下载完整文件，SHA-256 与本地安装包一致：

```text
6e2aea27c2df1f6170195ba0fe1f6b3cce62c5eb607283c8a693f889d3e2f354
```

## 后续维护

源码更新使用 Git 推送；新版安装包继续上传到对应 Release，并保持附件名 `WanShiWu-Setup.exe`，即可让 README 的“最新版”链接持续有效。安装包仍未商业签名，公开页面需要保留相关提示。
