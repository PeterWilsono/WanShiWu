<script setup lang="ts">
import type { Transaction } from '../types/transaction'
import { formatDateTime } from '../utils/time'
import CategoryIcon from './CategoryIcon.vue'
import MoneyText from './MoneyText.vue'

defineProps<{
  items: Transaction[]
  actionId: number | null
  timeZone: string
}>()
const emit = defineEmits<{
  edit: [transaction: Transaction]
  delete: [transaction: Transaction]
}>()

const sourceLabels: Record<Transaction['source'], string> = {
  manual: '手动记录',
  assistant: 'AI 记录',
  pantry: '食材联动',
  trip: '旅行联动',
}
</script>

<template>
  <div class="transaction-list">
    <article v-for="item in items" :key="item.id" class="transaction-card">
      <div class="category-icon" aria-hidden="true"><CategoryIcon :icon="item.category.icon" :name="item.category.name" /></div>
      <div class="transaction-main">
        <div class="transaction-title">
          <h2>{{ item.category.name }}</h2>
          <el-tag size="small" :type="item.type === 'income' ? 'success' : 'info'">
            {{ item.type === 'income' ? '收入' : '支出' }}
          </el-tag>
        </div>
        <p class="transaction-time">{{ formatDateTime(item.occurred_at, timeZone) }}</p>
        <p v-if="item.note" class="transaction-note">{{ item.note }}</p>
        <p class="transaction-source">{{ sourceLabels[item.source] }}</p>
      </div>
      <div class="transaction-side">
        <MoneyText :amount-cents="item.amount_cents" :type="item.type" />
        <div class="transaction-actions">
          <el-button size="small" :disabled="actionId === item.id" @click="emit('edit', item)">
            编辑
          </el-button>
          <el-button
            size="small"
            type="danger"
            plain
            :loading="actionId === item.id"
            @click="emit('delete', item)"
          >
            删除
          </el-button>
        </div>
      </div>
    </article>
  </div>
</template>

<style scoped>
.transaction-list {
  display: grid;
  gap: 12px;
}

.transaction-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: #fff;
}

.category-icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 12px;
  background: #f0f5ff;
  color: #409eff;
  font-weight: 600;
}

.transaction-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.transaction-title h2 {
  font-size: 17px;
}

.transaction-time,
.transaction-note,
.transaction-source {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.5;
}

.transaction-time,
.transaction-source {
  color: #909399;
}

.transaction-note {
  color: #606266;
  white-space: pre-wrap;
}

.transaction-side {
  display: grid;
  justify-items: end;
  gap: 14px;
}

.transaction-actions {
  display: flex;
  gap: 8px;
}

.transaction-actions .el-button + .el-button {
  margin-left: 0;
}

@media (max-width: 640px) {
  .transaction-card {
    grid-template-columns: auto minmax(0, 1fr);
    align-items: start;
    padding: 16px;
  }

  .transaction-side {
    grid-column: 1 / -1;
    grid-template-columns: 1fr auto;
    align-items: center;
    justify-items: start;
  }
}

/* Editorial refinement */
.transaction-list { gap: 14px; }
.transaction-card { padding: 22px 24px; border-color: var(--line-soft); border-radius: 3px 20px 3px 3px; background: var(--paper-light); transition: border-color .25s ease, box-shadow .25s ease, transform .25s ease; }
.transaction-card:hover { border-color: var(--line); box-shadow: var(--shadow-soft); transform: translateY(-2px); }
.category-icon { width: 46px; height: 46px; border-radius: 14px 14px 14px 4px; color: var(--ink); background: var(--paper-deep); font-family: var(--font-display); }
.transaction-title h2 { font-family: var(--font-display); font-size: 19px; }
.transaction-time, .transaction-source { color: var(--ink-muted); }
.transaction-note { color: var(--ink-secondary); }
.transaction-side :deep(.money-text) { font-family: var(--font-display); font-size: 23px; letter-spacing: -.03em; }
@media (max-width: 640px) { .transaction-card { padding: 20px; } }
</style>
