<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import { ApiError } from '../api/http'
import { completeTodo, createTodo, deleteTodo, listTodos, updateTodo } from '../api/todos'
import { useAuthStore } from '../stores/auth'
import type { Recurrence, Todo, TodoCreateRequest, TodoSort, TodoStatus } from '../types/todo'

interface TodoFormState {
  title: string
  note: string
  dueAt: Date | null
  priority: 1 | 2 | 3
  recurrence: Recurrence
  tags: string[]
}

const authStore = useAuthStore()
const todos = ref<Todo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const loadError = ref('')
const actionId = ref<number | null>(null)
const statusFilter = ref<TodoStatus | ''>('')
const tagFilter = ref('')
const sort = ref<TodoSort>('due_at')
const order = ref<'asc' | 'desc'>('asc')

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const submitting = ref(false)
const formError = ref('')
const formRef = ref<FormInstance>()
const form = reactive<TodoFormState>(emptyForm())

const statusLabels: Record<TodoStatus, string> = {
  pending: '进行中',
  done: '已完成',
  cancelled: '已取消',
}
const recurrenceLabels: Record<Recurrence, string> = {
  none: '不重复',
  daily: '每日',
  weekly: '每周',
  monthly: '每月',
}
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新建待办' : '编辑待办'))
const knownTags = computed(() => [...new Set(todos.value.flatMap((todo) => todo.tags))].sort())
const userTimezone = computed(() => authStore.user?.timezone || 'Asia/Shanghai')
const rules: FormRules<TodoFormState> = {
  title: [
    { required: true, message: '请输入待办标题', trigger: 'blur' },
    { max: 200, message: '标题不能超过 200 个字符', trigger: 'blur' },
  ],
}

function emptyForm(): TodoFormState {
  return { title: '', note: '', dueAt: null, priority: 2, recurrence: 'none', tags: [] }
}

function resetForm(): void {
  Object.assign(form, emptyForm())
  formError.value = ''
  editingId.value = null
  formRef.value?.clearValidate()
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

async function loadTodos(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const result = await listTodos({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
      tag: tagFilter.value.trim() || undefined,
      sort: sort.value,
      order: order.value,
    })
    todos.value = result.items
    total.value = result.total
  } catch (error) {
    loadError.value = errorMessage(error, '待办加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function applyFilters(): void {
  page.value = 1
  void loadTodos()
}

function resetFilters(): void {
  statusFilter.value = ''
  tagFilter.value = ''
  sort.value = 'due_at'
  order.value = 'asc'
  page.value = 1
  void loadTodos()
}

function openCreate(): void {
  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
}

function openEdit(todo: Todo): void {
  dialogMode.value = 'edit'
  Object.assign(form, {
    title: todo.title,
    note: todo.note || '',
    dueAt: todo.due_at ? new Date(todo.due_at) : null,
    priority: todo.priority,
    recurrence: todo.recurrence,
    tags: [...todo.tags],
  })
  editingId.value = todo.id
  formError.value = ''
  dialogVisible.value = true
}

async function submitForm(): Promise<void> {
  formError.value = ''
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  if (form.recurrence !== 'none' && !form.dueAt) {
    formError.value = '周期性待办需要设置截止时间'
    return
  }

  const payload: TodoCreateRequest = {
    title: form.title.trim(),
    note: form.note.trim() || null,
    due_at: form.dueAt?.toISOString() || null,
    priority: form.priority,
    recurrence: form.recurrence,
    tags: form.tags,
  }
  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createTodo(payload)
      ElMessage.success('待办已创建')
      statusFilter.value = 'pending'
      page.value = 1
    } else if (editingId.value !== null) {
      await updateTodo(editingId.value, payload)
      ElMessage.success('待办已更新')
    }
    dialogVisible.value = false
    await loadTodos()
  } catch (error) {
    formError.value = errorMessage(error, '保存失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

async function handleComplete(todo: Todo): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定完成“${todo.title}”吗？`, '完成待办', {
      confirmButtonText: '完成',
      cancelButtonText: '再等等',
      type: 'success',
    })
  } catch {
    return
  }

  actionId.value = todo.id
  try {
    const result = await completeTodo(todo.id)
    ElMessage.success(
      result.next_todo
        ? `已完成，下一次截止：${formatDateTime(result.next_todo.due_at)}`
        : '待办已完成',
    )
    await loadTodos()
  } catch (error) {
    ElMessage.error(errorMessage(error, '完成失败，请稍后重试'))
  } finally {
    actionId.value = null
  }
}

async function handleDelete(todo: Todo): Promise<void> {
  try {
    await ElMessageBox.confirm(`删除“${todo.title}”后将不再显示，确定继续吗？`, '删除待办', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  actionId.value = todo.id
  try {
    await deleteTodo(todo.id)
    ElMessage.success('待办已删除')
    if (todos.value.length === 1 && page.value > 1) page.value -= 1
    await loadTodos()
  } catch (error) {
    ElMessage.error(errorMessage(error, '删除失败，请稍后重试'))
  } finally {
    actionId.value = null
  }
}

function formatDateTime(value: string | null): string {
  if (!value) return '未设置'
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: userTimezone.value,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

function isOverdue(todo: Todo): boolean {
  return todo.status === 'pending' && !!todo.due_at && new Date(todo.due_at) < new Date()
}

function statusTagType(status: TodoStatus): 'warning' | 'success' | 'info' {
  return status === 'pending' ? 'warning' : status === 'done' ? 'success' : 'info'
}

onMounted(loadTodos)
</script>

<template>
  <main class="todo-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">生活管家</p>
        <h1>待办</h1>
        <p class="page-subtitle">把要做的事放在这里，一次只专注下一步。</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="openCreate">新建待办</el-button>
      </div>
    </header>

    <el-card class="filter-card" shadow="never">
      <div class="filters">
        <el-select v-model="statusFilter" placeholder="全部状态" clearable class="status-filter">
          <el-option label="进行中" value="pending" />
          <el-option label="已完成" value="done" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-input
          v-model="tagFilter"
          placeholder="按标签筛选，例如：工作"
          clearable
          class="tag-filter"
          @keyup.enter="applyFilters"
        />
        <el-select v-model="sort" aria-label="排序字段" class="sort-filter">
          <el-option label="按截止时间" value="due_at" />
          <el-option label="按创建时间" value="created_at" />
          <el-option label="按优先级" value="priority" />
        </el-select>
        <el-select v-model="order" aria-label="排序方向" class="order-filter">
          <el-option label="升序" value="asc" />
          <el-option label="降序" value="desc" />
        </el-select>
        <el-button type="primary" plain @click="applyFilters">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </el-card>

    <el-alert
      v-if="loadError"
      :title="loadError"
      type="error"
      show-icon
      :closable="false"
      class="load-alert"
    >
      <el-button size="small" @click="loadTodos">重新加载</el-button>
    </el-alert>

    <section v-loading="loading" class="list-section" aria-live="polite">
      <div class="list-summary">共 {{ total }} 条待办</div>
      <el-empty v-if="!loading && !todos.length && !loadError" description="暂无符合条件的待办">
        <el-button type="primary" @click="openCreate">创建第一条待办</el-button>
      </el-empty>

      <div v-else class="todo-list">
        <article v-for="todo in todos" :key="todo.id" class="todo-card">
          <div class="todo-main">
            <div class="todo-badges">
              <el-tag size="small" :type="statusTagType(todo.status)" effect="light">
                {{ statusLabels[todo.status] }}
              </el-tag>
              <el-tag v-if="isOverdue(todo)" size="small" type="danger" effect="light">已逾期</el-tag>
              <el-tag v-if="todo.recurrence !== 'none'" size="small" effect="plain">
                {{ recurrenceLabels[todo.recurrence] }}重复
              </el-tag>
            </div>
            <h2 :class="{ 'todo-title--done': todo.status !== 'pending' }">{{ todo.title }}</h2>
            <p v-if="todo.note" class="todo-note">{{ todo.note }}</p>
            <div class="todo-meta">
              <span>截止：{{ formatDateTime(todo.due_at) }}</span>
              <span>优先级：{{ todo.priority === 3 ? '高' : todo.priority === 2 ? '中' : '低' }}</span>
              <span v-if="todo.completed_at">完成：{{ formatDateTime(todo.completed_at) }}</span>
            </div>
            <div v-if="todo.tags.length" class="todo-tags">
              <el-tag v-for="tag in todo.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
            </div>
          </div>
          <div class="todo-actions">
            <el-button
              v-if="todo.status === 'pending'"
              type="success"
              plain
              :loading="actionId === todo.id"
              @click="handleComplete(todo)"
            >
              完成
            </el-button>
            <el-button :disabled="actionId === todo.id" @click="openEdit(todo)">编辑</el-button>
            <el-button
              type="danger"
              plain
              :disabled="actionId === todo.id"
              @click="handleDelete(todo)"
            >
              删除
            </el-button>
          </div>
        </article>
      </div>

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @current-change="loadTodos"
        @size-change="applyFilters"
      />
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="min(560px, 92vw)"
      :close-on-click-modal="false"
    >
      <el-alert
        v-if="formError"
        :title="formError"
        type="error"
        show-icon
        :closable="false"
        class="form-alert"
      />
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="标题" prop="title" required>
          <el-input v-model="form.title" maxlength="200" placeholder="要做什么？" autofocus />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.note"
            type="textarea"
            :rows="3"
            maxlength="1000"
            placeholder="补充地点、方法或注意事项（可选）"
          />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="截止时间">
            <el-date-picker
              v-model="form.dueAt"
              type="datetime"
              format="YYYY-MM-DD HH:mm"
              placeholder="选择日期和时间"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="优先级">
            <el-select v-model="form.priority" class="full-width">
              <el-option label="低" :value="1" />
              <el-option label="中" :value="2" />
              <el-option label="高" :value="3" />
            </el-select>
          </el-form-item>
          <el-form-item label="重复周期">
            <el-select v-model="form.recurrence" class="full-width">
              <el-option v-for="(label, value) in recurrenceLabels" :key="value" :label="label" :value="value" />
            </el-select>
          </el-form-item>
          <el-form-item label="标签">
            <el-select
              v-model="form.tags"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              placeholder="输入后回车创建标签"
              class="full-width"
            >
              <el-option v-for="tag in knownTags" :key="tag" :label="tag" :value="tag" />
            </el-select>
          </el-form-item>
        </div>
        <p v-if="form.recurrence !== 'none'" class="form-hint">
          完成当前待办时，会自动生成下一次{{ recurrenceLabels[form.recurrence] }}待办。
        </p>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<style scoped>
.todo-page {
  width: min(1120px, 100%);
  margin: 0 auto;
  padding: 40px 24px 56px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.page-eyebrow {
  margin-bottom: 6px;
  color: #409eff;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.12em;
}

.page-header h1 {
  margin-bottom: 8px;
  font-size: 32px;
}

.page-subtitle {
  color: #909399;
  line-height: 1.6;
}

.header-actions {
  display: flex;
  flex-shrink: 0;
  gap: 12px;
}

.header-actions .el-button + .el-button,
.todo-actions .el-button + .el-button {
  margin-left: 0;
}

.filter-card {
  margin-bottom: 20px;
  border: none;
  border-radius: 12px;
}

.filters {
  display: grid;
  grid-template-columns: 140px minmax(180px, 1fr) 150px 100px auto auto;
  gap: 12px;
}

.filters .el-button + .el-button {
  margin-left: 0;
}

.load-alert,
.form-alert {
  margin-bottom: 20px;
}

.list-section {
  min-height: 220px;
}

.list-summary {
  margin-bottom: 12px;
  color: #909399;
  font-size: 14px;
}

.todo-list {
  display: grid;
  gap: 12px;
}

.todo-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 22px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: #fff;
}

.todo-main {
  min-width: 0;
}

.todo-badges,
.todo-tags,
.todo-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.todo-badges {
  margin-bottom: 10px;
}

.todo-card h2 {
  overflow-wrap: anywhere;
  font-size: 18px;
  line-height: 1.5;
}

.todo-title--done {
  color: #909399;
  text-decoration: line-through;
}

.todo-note {
  margin-top: 6px;
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
}

.todo-meta {
  margin-top: 12px;
  color: #909399;
  font-size: 13px;
}

.todo-tags {
  margin-top: 10px;
}

.todo-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
}

.pagination {
  justify-content: flex-end;
  margin-top: 24px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 16px;
}

.full-width {
  width: 100%;
}

.form-hint {
  margin-top: -4px;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .filters {
    grid-template-columns: 1fr 1fr;
  }

  .tag-filter {
    grid-column: span 1;
  }
}

@media (max-width: 640px) {
  .todo-page {
    padding: 24px 16px 40px;
  }

  .page-header,
  .todo-card {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions,
  .todo-actions {
    width: 100%;
  }

  .header-actions .el-button,
  .todo-actions .el-button {
    flex: 1;
  }

  .filters,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .pagination {
    justify-content: center;
    overflow-x: auto;
  }
}

/* Editorial refinement */
.todo-page { width: min(1240px, 100%); padding: 58px 36px 80px; }
.page-header { margin-bottom: 38px; }
.page-header h1 { margin-bottom: 12px; font-size: 44px; }
.page-subtitle { font-size: 14px; }
.filter-card { margin-bottom: 28px; border: 1px solid var(--line-soft); background: rgb(251 250 246 / 58%); box-shadow: none; }
.filter-card :deep(.el-card__body) { padding: 18px; }
.list-summary { margin-bottom: 18px; color: var(--ink-muted); font-size: 11px; font-weight: 600; letter-spacing: .1em; }
.todo-list { gap: 14px; }
.todo-card { position: relative; padding: 25px 26px; border-color: var(--line-soft); border-radius: 3px 20px 3px 3px; background: var(--paper-light); transition: border-color .25s ease, box-shadow .25s ease, transform .25s ease; }
.todo-card::before { position: absolute; top: 26px; bottom: 26px; left: 0; width: 2px; background: var(--sage); content: ''; opacity: 0; transition: opacity .25s ease; }
.todo-card:hover { border-color: var(--line); box-shadow: var(--shadow-soft); transform: translateY(-2px); }
.todo-card:hover::before { opacity: 1; }
.todo-card h2 { font-family: var(--font-display); font-size: 21px; font-weight: 600; }
.todo-note { color: var(--ink-secondary); font-size: 14px; }
.todo-meta { color: var(--ink-muted); font-size: 12px; }
.todo-actions .el-button { min-height: 34px; padding: 7px 14px; font-size: 12px; }
@media (max-width: 640px) {
  .todo-page { padding: 38px 18px 60px; }
  .page-header { gap: 20px; margin-bottom: 28px; }
  .page-header h1 { font-size: 38px; }
  .todo-card { padding: 22px 20px; }
}
</style>
