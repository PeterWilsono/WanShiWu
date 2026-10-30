# 阶段 2.13：账目详情、PATCH 修改与软删除

## 这一步在做什么

本阶段补齐单条账目的另外三个操作：

| 接口 | 作用 |
| --- | --- |
| `GET /api/v1/transactions/{id}` | 查看账目详情与分类摘要 |
| `PATCH /api/v1/transactions/{id}` | 局部修改金额、类型、分类、备注、时间或来源 |
| `DELETE /api/v1/transactions/{id}` | 软删除账目 |

至此，分类和账目的后端 CRUD 已形成完整闭环。

## 需要理解的知识

### 1. PATCH 仍然区分“未传”和“传 null”

使用 `exclude_unset` 只提取明确提交的字段：

- `{}`：不修改业务字段；
- 没传 `note`：备注保持原值；
- `"note": null`：清空备注。

金额、类型、分类、发生时间和来源不接受 `null`，因为有效账目不能缺少这些信息。金额继续接受严格整数分，浮点数、布尔值和非正数都会被拒绝。

### 2. 修改类型与分类必须合并校验

假设原记录是“支出 + 餐饮”。只提交：

```json
{
  "type": "income"
}
```

如果保存，记录就会变成“收入 + 餐饮”，违反业务规则。反过来，只把分类改成“工资”也会形成“支出 + 工资”。

因此 service 先计算：

```text
修改后类型   = 请求传了 type 就用新值，否则用原值
修改后分类id = 请求传了 category_id 就用新值，否则用原值
```

再用这组完整值检查分类归属和类型。只改其中一个导致不匹配时返回 42201，原记录不变；同时提交 `"type": "income"` 和收入分类才能成功。

### 3. 为什么同时维护 category relationship

数据库外键是 `category_id`，响应中的分类摘要来自 ORM 的 `transaction.category` relationship。

PATCH 改分类时，如果只更新外键而保留旧 relationship，当前响应可能仍显示旧分类。因此 service 显式同步：

```python
transaction.category = category
```

保证 `category_id` 和嵌套分类摘要一致。详情查询使用 `selectinload` 一次加载分类，避免额外逐条查询。

### 4. 软删除与历史引用

DELETE 只写入 `deleted_at`：

- 详情返回 40401；
- 列表不再显示；
- 重复删除返回 40401；
- 数据库行仍保留。

软删除不等于“这条记录从未存在”。所以已删除账目仍然保护其分类：分类删除检查会包含软删除账目，防止历史外键失去含义。本阶段用真实 API 串联测试验证了这一跨阶段规则。

### 5. 越权与不存在保持同样响应

详情、修改和删除都统一通过 `get_transaction`，查询同时限定：

```text
id + 当前 user_id + deleted_at IS NULL
```

其他用户、不存在和已删除的账目都返回“账目不存在”的 40401，不暴露数据是否存在。

## 代码如何配合

- `life/schemas.py`
  - 新增 `TransactionUpdate`；
  - 保留严格整数分、UTC 时间和字段长度校验；
  - 仅备注允许显式清空。
- `life/service.py`
  - `get_transaction` 统一有效记录查询与分类加载；
  - `update_transaction` 合并校验类型和分类，并同步 relationship；
  - `delete_transaction` 写入软删除时间。
- `life/router.py`
  - 注册详情、PATCH 和 DELETE 路由。
- `tests/test_life_transactions_api.py`
  - 新增详情、完整修改、空 PATCH、备注清空、非法输入、组合校验、越权、未登录、软删除及分类保护测试。

## 如何验证

```bash
cd backend
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -v
```

本阶段新增 **28 个测试场景**，完整后端回归为 **192 项全部通过**，Ruff 检查全部通过，未安装新依赖。

## 下一步

后端分类与账目 CRUD 已完成。下一阶段 2.14 将定义前端分类、账目 TypeScript 类型和 API 封装，之后实现记账页面。
