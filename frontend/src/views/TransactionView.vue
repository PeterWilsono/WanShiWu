<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

import { listCategories } from '../api/categories'
import { ApiError } from '../api/http'
import { deleteTransaction, listTransactions } from '../api/transactions'
import TransactionFilters from '../components/TransactionFilters.vue'
import TransactionFormDialog from '../components/TransactionFormDialog.vue'
import TransactionList from '../components/TransactionList.vue'
import { useAuthStore } from '../stores/auth'
import type { Category } from '../types/category'
import type { Transaction, TransactionListQuery } from '../types/transaction'
import { monthInputFor } from '../utils/time'

const authStore = useAuthStore()
const categories = ref<Category[]>([])
const transactions = ref<Transaction[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const loadError = ref('')
const categoryError = ref('')
const actionId = ref<number | null>(null)
const timeZone = computed(() => authStore.user?.timezone || 'Asia/Shanghai')
const filters = ref<TransactionListQuery>(defaultFilters())
const dialogVisible = ref(false)
const editingTransaction = ref<Transaction | null>(null)

function defaultFilters(): TransactionListQuery {
  return {
    month: monthInputFor(new Date().toISOString(), timeZone.value),
    sort: 'occurred_at',
    order: 'desc',
  }
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

async function loadCategories(): Promise<void> {
  categoryError.value = ''
  try {
    categories.value = await listCategories()
  } catch (error) {
    categoryError.value = errorMessage(error, '分类加载失败')
  }
}

async function loadTransactions(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const result = await listTransactions({
      ...filters.value,
      page: page.value,
      page_size: pageSize.value,
    })
    transactions.value = result.items
    total.value = result.total
  } catch (error) {
    loadError.value = errorMessage(error, '账目加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function applyFilters(): void {
  page.value = 1
  void loadTransactions()
}

function resetFilters(): void {
  filters.value = defaultFilters()
  applyFilters()
}

function openCreate(): void {
  editingTransaction.value = null
  dialogVisible.value = true
}

function openEdit(transaction: Transaction): void {
  editingTransaction.value = transaction
  dialogVisible.value = true
}

async function handleSaved(transaction: Transaction, mode: 'create' | 'edit'): Promise<void> {
  if (mode === 'create') {
    filters.value = { ...defaultFilters(), month: monthInputFor(transaction.occurred_at, timeZone.value) }
    page.value = 1
  }
  await loadTransactions()
}

async function handleDelete(transaction: Transaction): Promise<void> {
  try {
    await ElMessageBox.confirm('删除后这笔账目将不再显示，确定继续吗？', '删除账目', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  actionId.value = transaction.id
  try {
    await deleteTransaction(transaction.id)
    ElMessage.success('账目已删除')
    if (transactions.value.length === 1 && page.value > 1) page.value -= 1
    await loadTransactions()
  } catch (error) {
    ElMessage.error(errorMessage(error, '删除失败，请稍后重试'))
  } finally {
    actionId.value = null
  }
}

onMounted(() => {
  void loadCategories()
  void loadTransactions()
})
</script>

<template>
  <main class="transaction-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">生活管家</p>
        <h1>记账</h1>
        <p class="page-subtitle">记录每一笔收支，金额始终以整数分保存。</p>
      </div>
      <div class="header-actions">
        <el-button @click="$router.push({ name: 'home' })">返回首页</el-button>
        <el-button @click="$router.push({ name: 'stats' })">月度统计</el-button>
        <el-button @click="$router.push({ name: 'categories' })">分类管理</el-button>
        <el-button type="primary" @click="openCreate">记一笔</el-button>
      </div>
    </header>

    <TransactionFilters
      v-model="filters"
      :categories="categories"
      @apply="applyFilters"
      @reset="resetFilters"
    />
    <el-alert v-if="categoryError" :title="categoryError" type="warning" show-icon :closable="false">
      <el-button size="small" @click="loadCategories">重新加载分类</el-button>
    </el-alert>
    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false">
      <el-button size="small" @click="loadTransactions">重新加载</el-button>
    </el-alert>

    <section v-loading="loading" class="list-section" aria-live="polite">
      <div class="list-summary">共 {{ total }} 条账目</div>
      <el-empty v-if="!loading && !transactions.length && !loadError" description="暂无符合条件的账目">
        <el-button type="primary" @click="openCreate">记录第一笔</el-button>
      </el-empty>
      <TransactionList
        v-else
        :items="transactions"
        :action-id="actionId"
        :time-zone="timeZone"
        @edit="openEdit"
        @delete="handleDelete"
      />
      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @current-change="loadTransactions"
        @size-change="applyFilters"
      />
    </section>

    <TransactionFormDialog
      v-model="dialogVisible"
      :transaction="editingTransaction"
      :categories="categories"
      @saved="handleSaved"
    />
  </main>
</template>

<style scoped>
.transaction-page {
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: 40px 24px 56px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}
.page-eyebrow { margin-bottom: 6px; color: #409eff; font-size: 13px; font-weight: 600; }
.page-header h1 { margin-bottom: 8px; font-size: 32px; }
.page-subtitle { color: #909399; line-height: 1.6; }
.header-actions { display: flex; flex-shrink: 0; gap: 10px; }
.header-actions .el-button + .el-button { margin-left: 0; }
.el-alert { margin-bottom: 16px; }
.list-section { min-height: 220px; }
.list-summary { margin-bottom: 12px; color: #909399; font-size: 14px; }
.pagination { justify-content: flex-end; margin-top: 24px; }
@media (max-width: 700px) {
  .transaction-page { padding: 24px 16px 40px; }
  .page-header { flex-direction: column; }
  .header-actions { width: 100%; flex-wrap: wrap; }
  .header-actions .el-button { flex: 1; }
  .pagination { justify-content: center; overflow-x: auto; }
}
</style>
