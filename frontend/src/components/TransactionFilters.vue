<script setup lang="ts">
import { computed } from 'vue'

import type { Category, TransactionType } from '../types/category'
import type { TransactionListQuery } from '../types/transaction'

const props = defineProps<{
  modelValue: TransactionListQuery
  categories: Category[]
}>()
const emit = defineEmits<{
  'update:modelValue': [value: TransactionListQuery]
  apply: []
  reset: []
}>()

const month = computed({
  get: () => props.modelValue.month || '',
  set: (month: string) => update({ month: month || undefined }),
})
const type = computed({
  get: () => props.modelValue.type || '',
  set: (type: '' | TransactionType) =>
    update({ type: type || undefined, category_id: undefined }),
})
const categoryId = computed({
  get: () => props.modelValue.category_id || null,
  set: (categoryId: number | null) => update({ category_id: categoryId || undefined }),
})
const sort = computed({
  get: () => props.modelValue.sort || 'occurred_at',
  set: (sort: NonNullable<TransactionListQuery['sort']>) => update({ sort }),
})
const order = computed({
  get: () => props.modelValue.order || 'desc',
  set: (order: NonNullable<TransactionListQuery['order']>) => update({ order }),
})
const availableCategories = computed(() =>
  props.categories.filter((category) => !type.value || category.type === type.value),
)

function update(patch: TransactionListQuery): void {
  emit('update:modelValue', { ...props.modelValue, ...patch })
}
</script>

<template>
  <el-card class="filter-card" shadow="never">
    <div class="filters">
      <el-date-picker v-model="month" type="month" value-format="YYYY-MM" placeholder="全部月份" clearable />
      <el-select v-model="type" placeholder="全部收支">
        <el-option label="全部收支" value="" />
        <el-option label="支出" value="expense" />
        <el-option label="收入" value="income" />
      </el-select>
      <el-select v-model="categoryId" placeholder="全部分类" clearable filterable>
        <el-option
          v-for="category in availableCategories"
          :key="category.id"
          :label="category.name"
          :value="category.id"
        />
      </el-select>
      <el-select v-model="sort" aria-label="排序字段">
        <el-option label="按发生时间" value="occurred_at" />
        <el-option label="按金额" value="amount_cents" />
        <el-option label="按记录时间" value="created_at" />
      </el-select>
      <el-select v-model="order" aria-label="排序方向">
        <el-option label="降序" value="desc" />
        <el-option label="升序" value="asc" />
      </el-select>
      <div class="filter-actions">
        <el-button type="primary" plain @click="emit('apply')">查询</el-button>
        <el-button @click="emit('reset')">本月</el-button>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.filter-card {
  margin-bottom: 20px;
  border: none;
  border-radius: 12px;
}

.filters {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr)) auto;
  gap: 10px;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.filter-actions .el-button + .el-button {
  margin-left: 0;
}

@media (max-width: 1000px) {
  .filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .filters {
    grid-template-columns: 1fr;
  }
}

.filter-card { margin-bottom: 28px; border: 1px solid var(--line-soft); background: rgb(251 250 246 / 58%); box-shadow: none; }
.filter-card :deep(.el-card__body) { padding: 18px; }
</style>
