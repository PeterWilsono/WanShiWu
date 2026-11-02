# GitHub 维护指南

仓库地址：<https://github.com/PeterWilsono/WanShiWu>

本文用于后续维护。普通使用者无需阅读，直接从 [Releases](https://github.com/PeterWilsono/WanShiWu/releases/latest) 下载即可。

## 源码更新

```bash
git status
git diff --check
git add .
git commit -m "描述本次修改"
git push origin main
```

提交前必须确认：

- 不提交 `.env`、真实模型 Key、访问令牌或私钥。
- 不提交 `data/`、`backend/data/` 和其他 SQLite 数据库。
- 不提交 `.venv`、`node_modules`、缓存、日志和测试安装目录。
- 安装包通过 Release 分发，不提交到源码历史。
- `.env.example` 只保留占位符，不填真实配置。

可用以下命令检查敏感类型是否已被跟踪：

```bash
git ls-files "*.env" "*.db" "*.exe" "node_modules/*"
```

正常应当没有输出。若真实密钥曾进入公开仓库，应立即吊销并更换，再清理 Git 历史；只删除最新文件不够。

## 发布新版 Windows 安装包

1. 更新 `desktop/package.json` 中的版本号。
2. 完成测试、前端构建、桌面启动和覆盖安装验证。
3. 在 GitHub Releases 创建对应标签，例如 `v1.0.3`。
4. 将安装包命名为 `WanShiWu-Setup.exe` 后上传，保持 README 的最新版下载链接不变。
5. 在 Release 说明中写明系统要求、主要变化、已知限制和 SHA-256。
6. 发布后在未登录浏览器中验证仓库可读、安装包可下载。

计算校验值：

```bash
sha256sum "安装包路径.exe"
```

Windows 用户下载后可运行：

```powershell
certutil -hashfile WanShiWu-Setup.exe SHA256
```

## 公开仓库注意事项

- 不依赖 WorkBuddy 连接器也可以维护：Git 负责源码，GitHub 网页负责 Release。
- 不在 Issue、截图或日志中公开数据库、Token 和模型 Key。
- 不要为了排查网络问题关闭 SSL 验证。
- 新增第三方素材、字体、图片或代码时，检查其许可证是否允许再分发。
- 安装包未商业签名前，应持续保留“未知发布者”提示。
