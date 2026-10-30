# 阶段 1.2：数据库层、users 表与 Alembic 迁移

## 这一阶段在做什么

这一阶段让后端具备可靠保存数据的能力：建立 SQLAlchemy 数据库连接与会话，创建第一张 `users` 表，并用 Alembic 管理表结构变化。

用户注册、待办、账目、食材等数据最终都要持久化。所谓持久化，就是关闭服务再启动后数据仍然存在，而不是只放在内存里。

## 主要文件

- `backend/app/core/time.py`：统一获取带时区的 UTC 当前时间。
- `backend/app/db/session.py`：数据库引擎、连接 PRAGMA、会话工厂和 FastAPI 的 `get_db` 依赖。
- `backend/app/db/types.py`：自定义 `UTCDateTime`，解决 SQLite 时区丢失问题。
- `backend/app/db/base.py`：所有模型继承的 `Base`，以及通用时间、软删除字段。
- `backend/app/modules/auth/models.py`：`User` 模型，对应 `users` 表。
- `backend/alembic/`：数据库迁移配置和版本脚本。
- `backend/tests/conftest.py`：每个测试使用独立内存数据库的公共设施。
- `backend/tests/test_db_users.py`：验证用户 CRUD、用户名唯一、外键和 WAL。

## 用到的主要知识

### 1. ORM 与 SQLAlchemy

ORM（对象关系映射）把数据库表映射成 Python 类，把一行数据映射成对象。例如 `User` 对应 `users` 表，`user.username` 对应这一行的用户名字段。

这不意味着完全不关心数据库。唯一约束、外键、事务和索引仍然需要明确设计，ORM 只是让日常操作更类型化、更容易维护。

### 2. 引擎、会话和 `get_db`

- Engine：管理数据库连接。
- Session：一次业务操作的工作单元，负责查询、添加、提交或回滚。
- `get_db`：FastAPI 依赖，每个请求获得一个会话，请求结束后自动关闭。

依赖注入让测试可以把真实数据库替换为内存数据库，而业务代码不用改变。

### 3. 为什么时间统一使用 UTC

如果服务器、数据库和用户分别使用本地时间，跨时区或夏令时场景很容易出错。项目约定数据库存 UTC，显示时再转成用户时区（默认 `Asia/Shanghai`）。

`now_utc()` 是全项目获取当前时间的统一入口。以后测试「明天到期」等逻辑时，可以替换时间来源，不必修改业务代码。

### 4. SQLite 为什么会丢时区，怎样解决

SQLite 的日期时间本质上没有完整的时区类型。普通 `DateTime(timezone=True)` 写入后，再读出来可能变成不带时区的 `datetime`，与带时区时间比较会抛出 `TypeError`。

自定义 `UTCDateTime` 做了两件事：

1. 写入前把带时区时间转换成 UTC；不接受不带时区的时间，避免含义不明。
2. 读出后如果 SQLite 返回 naive datetime，就补回 UTC 时区。

这样业务层始终处理 aware datetime，后续提醒扫描和日程比较会更安全。

### 5. 外键与 WAL 两个 PRAGMA

- `PRAGMA foreign_keys=ON`：让 SQLite 真正执行外键约束，防止出现「明细指向一条不存在的主记录」。
- `PRAGMA journal_mode=WAL`：写前日志模式，改善读写并发，降低读写互相阻塞的概率。

它们必须在连接建立时设置，所以代码监听 Engine 的 `connect` 事件，而不是只在某次启动时执行一次。

### 6. Alembic 迁移

迁移脚本描述数据库结构从一个版本到另一个版本怎样变化。新环境不必手工点表或执行零散文档里的 SQL，只要运行：

```bash
.venv/Scripts/python.exe -m alembic upgrade head
```

就能升级到最新结构。每次模型需要改表时，都要生成并审查迁移，不允许直接手改正式数据库来绕过版本记录。

### 7. 唯一约束与 CRUD

CRUD 是创建、读取、更新、删除。`username` 上的 `unique=True` 会生成数据库唯一约束，即使两段代码同时误判「用户名可用」，数据库仍会阻止重复用户名，这是最后一道数据完整性保障。

### 8. 内存数据库与 StaticPool

测试使用 `sqlite:///:memory:`，速度快且不会碰真实数据。普通内存库每个连接都是独立数据库，因此测试使用 `StaticPool` 共享同一连接，保证建表会话和测试会话看到同一份数据。

每个测试结束都会删表并释放引擎，避免一个测试的数据污染另一个测试。

## users 表当前包含什么

`id`、`username`、`password_hash`、`timezone`、`settings_json`、`created_at`。这里只保存密码哈希，不保存原始密码。哈希与登录流程会在阶段 1.3 接入。

数据库文件位于 D 盘项目内的 `backend/data/wanshiwu.db`，并已通过 `.gitignore` 排除，不会提交到 Git。

## 本阶段发现并修复的问题

1. 测试最初没有导入 session 模块，导致 PRAGMA 监听器未注册；补上导入后，测试环境与应用环境一致。
2. 测试发现 SQLite 读回 naive datetime；增加 `UTCDateTime` 后，读写都保持 aware UTC。
3. Alembic 自动生成文件使用其模板风格，项目让 Ruff 排除 `alembic/`，不为了格式检查手改自动生成文件。

## 如何验证

```bash
cd backend
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m pytest tests/test_db_users.py -v
```

本阶段全部 9 个测试通过，真实数据库迁移成功，用户 CRUD、用户名唯一约束、外键开启和文件库 WAL 均有测试覆盖。
