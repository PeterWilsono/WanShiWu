# 阶段 2.14：前端分类、账目类型与 API 封装

## 这一步做什么

把后端已经完成的分类和记账接口翻译成前端容易使用的 TypeScript 类型与函数，并统一金额、时间的转换入口。下一步页面只需要处理用户交互，不需要重复写 URL、请求头或响应拆解。

## 涉及的知识

- **TypeScript 接口（interface）**：描述一份数据应该有哪些字段。它与后端 Pydantic Schema 对应，能在构建时发现字段拼写或类型错误。
- **整数分**：`12.34 元` 在 API 中是 `1234` 分。后端不收浮点金额，前端也不能直接用 `12.34 * 100`，因为二进制浮点可能产生微小误差。
- **PATCH 的可选字段**：`note?: string | null` 中，不传 `note` 表示不修改，传 `null` 表示清空，传字符串表示改成新备注。
- **自然月与时区**：查询参数只传 `YYYY-MM`，由后端根据用户时区确定月份边界，前端不自行猜 UTC 区间。
- **关联数据**：每条账目已经带有 `category` 摘要，页面不需要为每条记录额外请求分类。

## 新增文件

- `src/types/category.ts`：分类、收支类型、新建和修改参数。
- `src/types/transaction.ts`：账目、来源、查询、分页、新建和修改参数。
- `src/api/categories.ts`：分类列表、新建、改名和删除。
- `src/api/transactions.ts`：账目列表、新建、详情、修改和删除。
- `src/utils/money.ts`：严格的元分转换与千分位展示。
- `src/utils/time.ts`：按用户时区格式化时间，以及当前月份输入值。

## 金额如何转换

`yuanToCents()` 先用正则限制输入格式，再分别读取“元”和最多两位“小数”，用整数计算：

```text
19.9 元 → 19 × 100 + 90 = 1990 分
```

零、负数、超过两位小数、文字和超出 JavaScript 安全整数范围的值都会被拒绝。`formatMoney()` 反向把整数分格式化为 `¥1,234.50`，`formatTransactionMoney()` 再根据收支添加正负号。

## 页面如何使用

```ts
const result = await listTransactions({ month: '2026-10', type: 'expense' })
const transaction = await createTransaction({
  amount_cents: 1990,
  type: 'expense',
  category_id: 1,
  occurred_at: new Date().toISOString(),
})
```

这些函数自动复用 Token 注入、401 处理和 `ApiError`，页面不会直接调用 Axios。

## 如何验证

执行 `cd frontend && npm run build`，`vue-tsc` 类型检查与 Vite 生产构建均通过。只有既有的 Element Plus 主包体积提示，不影响功能。

本阶段是基础设施，没有页面和浏览器交互，因此不把构建通过等同于人工联调通过。金额转换与页面联动会在下一阶段实际接入。
