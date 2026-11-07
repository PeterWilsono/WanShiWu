# 阶段 19：桌面版数据位置（不强制放 C 盘、可自行迁移）

## 这次要解决的问题

旧版 Windows 桌面软件把账号和业务数据固定放在：

```
%LOCALAPPDATA%\WanShiWu\data
```

这个路径在系统盘（通常是 C 盘）。用户提出三点要求：

1. 默认不要放 C 盘，跟着软件安装的位置走（装在 D 盘就放在 D 盘的 `data`）。
2. 已经存在 C 盘的数据要迁移过去。
3. 最好在软件里能自己选保存位置。

## 背景知识

- **Electron 只是外壳**：界面跑在 Electron 里，真正的数据库由内嵌的 Python 后端进程（`wanshiwu-backend.exe`）读写。所以数据目录必须在内嵌进程启动**之前**定好，通过环境变量 `WANSHIWU_DATA_DIR` 传进去。
- **为什么不能只写在数据库里**：数据库自己就存在这个目录里，属于“先有鸡还是先有蛋”。因此位置记录必须放在数据库之外的独立小文件里。
- **SQLite 与运行中复制**：数据库运行时会有 `-wal`、`-shm` 辅助文件。直接复制运行中的库可能得到不一致的副本，所以迁移前必须先让后端进程退出。
- **卸载风险**：数据放在安装目录内，卸载软件时容易被一并删除。这一点在设置页和文档里都写清楚了，长期使用可以选择独立文件夹。

## 实现方案

### 1. 数据目录的解析顺序（`desktop/data-location.js`）

| 优先级 | 来源 | 说明 |
| --- | --- | --- |
| 1 | 环境变量 `WANSHIWU_DATA_DIR` | 开发、测试和自动化验收使用 |
| 2 | 用户设置文件 `%LOCALAPPDATA%\WanShiWu\data-location.json` | 在软件里改过位置后写入 |
| 3 | **安装目录下的 `data`** | 默认值，装在 D 盘就在 D 盘 |
| 4 | `%LOCALAPPDATA%\WanShiWu\data` | 安装目录不可写，或位于系统临时目录时回退 |

“不可写”和“在临时目录”两种判断很关键：软件如果从压缩包临时解压目录运行，把数据写进临时目录会在重启后被清理。

### 2. 首次启动自动迁移

启动时如果满足三个条件——新位置还没有数据库、旧位置（`%LOCALAPPDATA%\WanShiWu\data`）存在数据库、两者不是同一个目录——就复制 `wanshiwu.db`、`wanshiwu.db-wal`、`wanshiwu.db-shm`、`jwt-secret.txt`，并逐个校验文件大小。

复制失败时**不删除**任何东西，并且继续使用旧位置启动。否则软件会新建一个空库，用户看到的就是“数据全没了”。

### 3. 软件内更换位置

“我的 → 设置 → 数据存储”里可以看到：

- 真实保存路径、保存规则（安装目录内 / 自定义位置 / 系统本地目录 / 临时回退）
- 所在磁盘，若在 C 盘会给出提示
- 运行日志路径、位置记录文件路径
- 旧位置是否还留有副本

点击“更换保存位置”：

1. 先确认一次（说明会复制、校验并重启）。
2. 选择目标文件夹。
3. 后端进程先退出，避免复制到一半的数据库。
4. 复制 + 校验大小，失败会清理半成品并保留原数据。
5. 写入位置记录，自动重启软件。

目标文件夹若已有万事屋数据，会明确询问是“使用这里的已有数据”还是取消，不会静默覆盖任何一边。

### 4. 权限收紧

Electron 页面原本没有 preload。这次新增 `preload.js`，只通过 `contextBridge` 暴露四个受控方法（读取位置、选择位置、打开当前文件夹、打开旧文件夹），页面拿不到任意文件读写能力。

## 涉及文件

| 文件 | 职责 |
| --- | --- |
| `desktop/data-location.js` | 目录解析、可写判断、迁移与校验（不依赖 Electron，可单测） |
| `desktop/preload.js` | 只暴露数据位置相关能力 |
| `desktop/main.js` | 启动前定目录、传入环境变量、IPC、迁移后重启 |
| `desktop/tests/data-location.test.js` | 10 项单元测试 |
| `frontend/src/views/SettingsView.vue` | “数据存储”页签 |
| `frontend/src/types/desktop.ts` | preload 桥接的类型声明 |
| `frontend/src/components/AppIcon.vue` | 新增文件夹图标 |

## 验证

- `npm --prefix desktop test`：10 项全部通过（默认安装目录、临时目录回退、用户设置优先、指针失效回退、环境变量优先、迁移复制、已有库不覆盖、旧位置无数据、主动迁移、非法目标拒绝），连续两次运行稳定。
- `electron . --probe-data-location`：真实解析出 `install` 规则，并把 C 盘数据迁移到安装目录，日志出现 `WANSHIWU_DATA_MIGRATED`。
- 打包后程序 `WanShiWu.exe --smoke-test`：`WANSHIWU_DESKTOP_DATA_DIR D:\WanShiWu\data (custom)` 与 `WANSHIWU_DESKTOP_SMOKE_OK`，说明位置记录生效、本地服务用新目录启动成功。
- 真实窗口（Chrome DevTools 协议连接打包程序）：
  - `window.wanshiwuDesktop` 只有 5 个键（`isDesktop` 与 4 个方法），未暴露任意文件权限。
  - 页面读取的真实路径为 `D:\...\.ui-data-b`，保存规则、所在磁盘、日志、位置记录四行与 IPC 返回一致。
  - 1280 与 1024 宽度均无横向溢出，页面脚本错误 0。
- `npm run build`（前端）：`vue-tsc` 类型检查与生产构建通过。
- 安装包：`desktop/artifacts/WanShiWu-Windows-1.0.3-setup.exe`，167,131,196 字节，版本 1.0.3。
- 截图证据：`desktop/artifacts/desktop-05-storage-real.png`（真实窗口）、`desktop-02-storage-1280.png`（浏览器桥接模拟）。

## 边界与已知限制

- 卸载程序会清理安装目录，数据若在里面会一起被删除；设置页已提示，建议长期使用放到独立文件夹。
- 原生文件夹选择框无法用脚本点击，自动化只覆盖“解析、迁移、校验”逻辑，选择动作需在真实窗口内人工确认。
- 位置记录文件 `data-location.json` 仍放在 `%LOCALAPPDATA%\WanShiWu\`，只有几十字节，用于在数据库之外记住用户的选择。
- 软件运行中不能迁移（会先退出后端进程再复制）；如果旧版实例还开着，新版因单实例限制不会启动，需要先关闭旧窗口。
- 本机已把位置记录指向 `D:\WanShiWu\data`，实际迁移发生在安装 1.0.3 后首次启动时，届时按当时的 C 盘数据复制，旧位置保留副本。
