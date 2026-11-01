<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

import { deleteCategory, listCategories } from '../api/categories'
import { ApiError } from '../api/http'
import CategoryFormDialog from '../components/CategoryFormDialog.vue'
import CategoryIcon from '../components/CategoryIcon.vue'
import type { Category, TransactionType } from '../types/category'

const categories = ref<Category[]>([])
const activeType = ref<TransactionType>('expense')
const loading = ref(false)
const loadError = ref('')
const actionId = ref<number | null>(null)
const dialogVisible = ref(false)
const editingCategory = ref<Category | null>(null)
const visibleCategories = computed(() =>
  categories.value.filter((category) => category.type === activeType.value),
)
const counts = computed(() => ({
  expense: categories.value.filter((category) => category.type === 'expense').length,
  income: categories.value.filter((category) => category.type === 'income').length,
}))

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

async function loadCategories(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    categories.value = await listCategories()
  } catch (error) {
    loadError.value = errorMessage(error, '分类加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editingCategory.value = null
  dialogVisible.value = true
}

function openEdit(category: Category): void {
  editingCategory.value = category
  dialogVisible.value = true
}

async function handleSaved(category: Category): Promise<void> {
  activeType.value = category.type
  await loadCategories()
}

async function handleDelete(category: Category): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除“${category.name}”吗？已有账目引用的分类不能删除，只能改名。`,
      '删除分类',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  actionId.value = category.id
  try {
    await deleteCategory(category.id)
    ElMessage.success('分类已删除')
    await loadCategories()
  } catch (error) {
    ElMessage.error(errorMessage(error, '删除失败，请稍后重试'))
  } finally {
    actionId.value = null
  }
}

onMounted(loadCategories)
</script>

<template>
  <main class="category-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">生活管家 · 设置</p>
        <h1>分类管理</h1>
        <p class="page-subtitle">用适合自己的分类整理收支，历史账目的分类关系会受到保护。</p>
      </div>
      <div class="header-actions">
        <el-button @click="$router.push({ name: 'transactions' })">返回记账</el-button>
        <el-button type="primary" @click="openCreate">新建分类</el-button>
      </div>
    </header>

    <el-alert
      title="内置分类可改名但不可删除；已被任何账目引用的自定义分类也只能改名。"
      type="info"
      show-icon
      :closable="false"
      class="rule-alert"
    />
    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false">
      <el-button size="small" @click="loadCategories">重新加载</el-button>
    </el-alert>

    <el-tabs v-model="activeType" class="category-tabs">
      <el-tab-pane :label="`支出分类 (${counts.expense})`" name="expense" />
      <el-tab-pane :label="`收入分类 (${counts.income})`" name="income" />
    </el-tabs>

    <section v-loading="loading" class="category-section" aria-live="polite">
      <el-empty
        v-if="!loading && !visibleCategories.length && !loadError"
        description="当前类型暂无分类"
      >
        <el-button type="primary" @click="openCreate">新建分类</el-button>
      </el-empty>
      <div v-else class="category-grid">
        <article v-for="category in visibleCategories" :key="category.id" class="category-card">
          <div class="category-icon" aria-hidden="true"><CategoryIcon :icon="category.icon" :name="category.name" /></div>
          <div class="category-info">
            <div class="category-name">
              <h2>{{ category.name }}</h2>
              <el-tag v-if="category.is_default" size="small" type="info">内置</el-tag>
              <el-tag v-else size="small" type="success">自定义</el-tag>
            </div>
            <p>{{ category.type === 'expense' ? '支出' : '收入' }}分类</p>
          </div>
          <div class="category-actions">
            <el-button size="small" :disabled="actionId === category.id" @click="openEdit(category)">
              编辑
            </el-button>
            <el-tooltip
              :content="category.is_default ? '内置分类不可删除' : '删除分类'"
              placement="top"
            >
              <span>
                <el-button
                  size="small"
                  type="danger"
                  plain
                  :disabled="category.is_default"
                  :loading="actionId === category.id"
                  @click="handleDelete(category)"
                >
                  删除
                </el-button>
              </span>
            </el-tooltip>
          </div>
        </article>
      </div>
    </section>

    <CategoryFormDialog
      v-model="dialogVisible"
      :category="editingCategory"
      :default-type="activeType"
      @saved="handleSaved"
    />
  </main>
</template>

<style scoped>
.category-page { width: min(1080px, 100%); margin: 0 auto; padding: 40px 24px 56px; }
.page-header { display: flex; justify-content: space-between; gap: 24px; margin-bottom: 24px; }
.page-eyebrow { margin-bottom: 6px; color: #409eff; font-size: 13px; font-weight: 600; }
.page-header h1 { margin-bottom: 8px; font-size: 32px; }
.page-subtitle { color: #909399; line-height: 1.6; }
.header-actions { display: flex; flex-shrink: 0; gap: 10px; }
.header-actions .el-button + .el-button { margin-left: 0; }
.rule-alert, .el-alert { margin-bottom: 16px; }
.category-tabs { margin-top: 8px; }
.category-section { min-height: 220px; }
.category-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.category-card {
  display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center;
  gap: 14px; padding: 18px; border: 1px solid #ebeef5; border-radius: 12px; background: #fff;
}
.category-icon {
  display: grid; width: 40px; height: 40px; place-items: center; border-radius: 10px;
  background: #f0f5ff; color: #409eff; font-weight: 600;
}
.category-name { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.category-name h2 { overflow-wrap: anywhere; font-size: 17px; }
.category-info p { margin-top: 5px; color: #909399; font-size: 13px; }
.category-actions { display: flex; gap: 8px; }
.category-actions .el-button + .el-button { margin-left: 0; }
@media (max-width: 760px) {
  .category-page { padding: 24px 16px 40px; }
  .page-header { flex-direction: column; }
  .header-actions .el-button { flex: 1; }
  .category-grid { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
  .category-card { grid-template-columns: auto minmax(0, 1fr); }
  .category-actions { grid-column: 1 / -1; justify-content: flex-end; }
}

/* Editorial refinement */
.category-page { width: min(1160px, 100%); padding: 58px 36px 80px; }
.page-header { align-items: flex-start; margin-bottom: 34px; }
.page-header h1 { margin-bottom: 12px; font-size: 44px; }
.page-subtitle { font-size: 14px; }
.rule-alert { margin: 0 0 24px; background: rgb(251 250 246 / 60%); }
.category-grid { gap: 16px; }
.category-card { padding: 22px; border-color: var(--line-soft); border-radius: 3px 18px 3px 3px; background: var(--paper-light); transition: border-color .25s ease, box-shadow .25s ease, transform .25s ease; }
.category-card:hover { border-color: var(--line); box-shadow: var(--shadow-soft); transform: translateY(-2px); }
.category-icon { width: 44px; height: 44px; border-radius: 13px 13px 13px 4px; color: var(--ink); background: var(--paper-deep); font-family: var(--font-display); }
.category-name h2 { font-family: var(--font-display); font-size: 19px; }
.category-info p { color: var(--ink-muted); }
@media (max-width: 760px) {
  .category-page { padding: 38px 18px 60px; }
  .page-header h1 { font-size: 38px; }
}
</style>
