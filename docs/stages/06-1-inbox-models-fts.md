# 阶段 6.1：收藏箱数据模型与全文索引

> 对应权威说明书的“阶段 6 收藏箱”。此前 `06-visual-system-refinement.md` 是额外视觉专项，不改变本模块的需求编号。

## 目标

建立收藏箱的数据基础：收藏链接、处理状态、标签、多对多关联、每周回顾，以及支持中文子串检索的 SQLite FTS5 索引。

## 主要文件

- `backend/app/modules/inbox/models.py`：`bookmarks`、`tags`、`bookmark_tags`、`weekly_digests` 与状态枚举。
- `backend/app/modules/inbox/fts.py`：FTS5 建表、写入更新和删除函数。
- `backend/alembic/versions/08e2c76c6a1b_create_inbox_tables.py`：正式迁移，包含普通表与虚拟表。
- `backend/tests/conftest.py`：内存测试库同样显式创建 FTS5，避免测试环境与迁移不一致。

## 关键设计

- 每个收藏和标签都带 `user_id`，并延续 UTC 时间与软删除约定。
- 同一用户的 URL、标签名分别唯一；标签关联记录 `manual` 或 `ai` 来源。
- FTS 的 `rowid` 与收藏 ID 一致，业务表和索引将在同一个 service 事务中更新。
- `trigram` 支持中文及英文子串搜索；1～2 个字符的查询将在搜索接口退化为 LIKE。
- 软删除记录仍占用 URL 唯一约束，因此后续新增收藏遇到已删除的同 URL 时会恢复该记录，而不是报无法解释的冲突。

## 验证

- 已执行开发库 `alembic upgrade head`，当前版本为 `08e2c76c6a1b (head)`。
- 收藏模型接入后，认证回归 10 项通过。
- 新增模块 Ruff 检查通过。

## 下一步

实现收藏 CRUD、手动标签、状态筛选与全文搜索，再接入后台抓取和 AI 摘要。
