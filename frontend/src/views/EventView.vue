<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import { createEvent, deleteEvent, listEvents, updateEvent } from '../api/events'
import { ApiError } from '../api/http'
import { useAuthStore } from '../stores/auth'
import type { Event, EventCreateRequest } from '../types/event'

interface EventFormState {
  title: string
  startAt: Date | null
  endAt: Date | null
  allDay: boolean
  location: string
  remindBeforeMin: number | null
  note: string
}

const authStore = useAuthStore()
const events = ref<Event[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const loadError = ref('')
const actionId = ref<number | null>(null)
const dateRange = ref<[Date, Date] | null>(monthRangeFor(new Date()))

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const submitting = ref(false)
const formError = ref('')
const formRef = ref<FormInstance>()
const form = reactive<EventFormState>(emptyForm())

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新建日程' : '编辑日程'))
const userTimezone = computed(() => authStore.user?.timezone || 'Asia/Shanghai')
const rules: FormRules<EventFormState> = {
  title: [
    { required: true, message: '请输入日程标题', trigger: 'blur' },
    { max: 200, message: '标题不能超过 200 个字符', trigger: 'blur' },
  ],
  startAt: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
}

function emptyForm(): EventFormState {
  return {
    title: '',
    startAt: null,
    endAt: null,
    allDay: false,
    location: '',
    remindBeforeMin: null,
    note: '',
  }
}

function monthRangeFor(date: Date): [Date, Date] {
  const start = new Date(date.getFullYear(), date.getMonth(), 1)
  const end = new Date(date.getFullYear(), date.getMonth() + 1, 1)
  end.setMilliseconds(end.getMilliseconds() - 1)
  return [start, end]
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

async function loadEvents(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const result = await listEvents({
      page: page.value,
      page_size: pageSize.value,
      range_start: dateRange.value?.[0].toISOString(),
      range_end: dateRange.value?.[1].toISOString(),
    })
    events.value = result.items
    total.value = result.total
  } catch (error) {
    loadError.value = errorMessage(error, '日程加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function applyFilters(): void {
  page.value = 1
  void loadEvents()
}

function resetFilters(): void {
  dateRange.value = monthRangeFor(new Date())
  page.value = 1
  void loadEvents()
}

function openCreate(): void {
  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
}

function openEdit(event: Event): void {
  dialogMode.value = 'edit'
  Object.assign(form, {
    title: event.title,
    startAt: new Date(event.start_at),
    endAt: event.end_at ? new Date(event.end_at) : null,
    allDay: event.all_day,
    location: event.location || '',
    remindBeforeMin: event.remind_before_min,
    note: event.note || '',
  })
  editingId.value = event.id
  formError.value = ''
  formRef.value?.clearValidate()
  dialogVisible.value = true
}

async function submitForm(): Promise<void> {
  formError.value = ''
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  if (!form.startAt) {
    formError.value = '请选择开始时间'
    return
  }
  if (form.endAt && form.endAt < form.startAt) {
    formError.value = '结束时间不能早于开始时间'
    return
  }

  const payload: EventCreateRequest = {
    title: form.title.trim(),
    start_at: form.startAt.toISOString(),
    end_at: form.endAt?.toISOString() || null,
    all_day: form.allDay,
    location: form.location.trim() || null,
    remind_before_min: form.remindBeforeMin,
    note: form.note.trim() || null,
  }
  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createEvent(payload)
      ElMessage.success('日程已创建')
      // 切换到新日程所在月份，避免创建后因为当前筛选窗口而看不到它。
      dateRange.value = monthRangeFor(new Date(payload.start_at))
      page.value = 1
    } else if (editingId.value !== null) {
      await updateEvent(editingId.value, payload)
      ElMessage.success('日程已更新')
    }
    dialogVisible.value = false
    await loadEvents()
  } catch (error) {
    formError.value = errorMessage(error, '保存失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(event: Event): Promise<void> {
  try {
    await ElMessageBox.confirm(`删除“${event.title}”后将不再显示，确定继续吗？`, '删除日程', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  actionId.value = event.id
  try {
    await deleteEvent(event.id)
    ElMessage.success('日程已删除')
    if (events.value.length === 1 && page.value > 1) page.value -= 1
    await loadEvents()
  } catch (error) {
    ElMessage.error(errorMessage(error, '删除失败，请稍后重试'))
  } finally {
    actionId.value = null
  }
}

function formatDateTime(value: string): string {
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

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: userTimezone.value,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value))
}

function formatEventTime(event: Event): string {
  if (event.all_day) {
    const start = formatDate(event.start_at)
    const end = event.end_at ? formatDate(event.end_at) : null
    return end && end !== start ? `${start} 至 ${end} · 全天` : `${start} · 全天`
  }
  const start = formatDateTime(event.start_at)
  return event.end_at ? `${start} 至 ${formatDateTime(event.end_at)}` : start
}

function formatReminder(minutes: number | null): string {
  if (minutes === null) return ''
  if (minutes === 0) return '到点提醒'
  if (minutes < 60) return `提前 ${minutes} 分钟`
  if (minutes % 1440 === 0) return `提前 ${minutes / 1440} 天`
  if (minutes % 60 === 0) return `提前 ${minutes / 60} 小时`
  return `提前 ${minutes} 分钟`
}

function isPast(event: Event): boolean {
  return new Date(event.end_at || event.start_at) < new Date()
}

onMounted(loadEvents)
</script>

<template>
  <main class="event-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">生活管家</p>
        <h1>日程</h1>
        <p class="page-subtitle">安排明确的时间，也给临时变化留出空间。</p>
      </div>
      <div class="header-actions">
        <el-button @click="$router.push({ name: 'home' })">返回首页</el-button>
        <el-button type="primary" @click="openCreate">新建日程</el-button>
      </div>
    </header>

    <el-card class="filter-card" shadow="never">
      <div class="filters">
        <el-date-picker
          v-model="dateRange"
          type="datetimerange"
          format="YYYY-MM-DD HH:mm"
          range-separator="至"
          start-placeholder="查询窗口开始"
          end-placeholder="查询窗口结束"
          clearable
          class="range-filter"
        />
        <el-button type="primary" plain @click="applyFilters">查询</el-button>
        <el-button @click="resetFilters">本月</el-button>
      </div>
      <p class="filter-hint">显示与时间窗口有重叠的日程；清空时间范围可查询全部。</p>
    </el-card>

    <el-alert
      v-if="loadError"
      :title="loadError"
      type="error"
      show-icon
      :closable="false"
      class="load-alert"
    >
      <el-button size="small" @click="loadEvents">重新加载</el-button>
    </el-alert>

    <section v-loading="loading" class="list-section" aria-live="polite">
      <div class="list-summary">共 {{ total }} 条日程</div>
      <el-empty v-if="!loading && !events.length && !loadError" description="暂无符合条件的日程">
        <el-button type="primary" @click="openCreate">创建第一条日程</el-button>
      </el-empty>

      <div v-else class="event-list">
        <article v-for="event in events" :key="event.id" class="event-card">
          <div class="event-main">
            <div class="event-badges">
              <el-tag v-if="event.all_day" size="small" type="success" effect="light">全天</el-tag>
              <el-tag v-if="event.remind_before_min !== null" size="small" effect="plain">
                {{ formatReminder(event.remind_before_min) }}
              </el-tag>
              <el-tag v-if="isPast(event)" size="small" type="info" effect="light">已结束</el-tag>
            </div>
            <h2>{{ event.title }}</h2>
            <p class="event-time">{{ formatEventTime(event) }}</p>
            <p v-if="event.location" class="event-location">地点：{{ event.location }}</p>
            <p v-if="event.note" class="event-note">{{ event.note }}</p>
          </div>
          <div class="event-actions">
            <el-button :disabled="actionId === event.id" @click="openEdit(event)">编辑</el-button>
            <el-button
              type="danger"
              plain
              :loading="actionId === event.id"
              @click="handleDelete(event)"
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
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @current-change="loadEvents"
        @size-change="applyFilters"
      />
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="min(600px, 92vw)"
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
          <el-input v-model="form.title" maxlength="200" placeholder="要安排什么？" autofocus />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="开始时间" prop="startAt" required>
            <el-date-picker
              v-model="form.startAt"
              type="datetime"
              format="YYYY-MM-DD HH:mm"
              placeholder="选择开始时间"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="结束时间">
            <el-date-picker
              v-model="form.endAt"
              type="datetime"
              format="YYYY-MM-DD HH:mm"
              placeholder="可选，清空表示单点日程"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="全天日程">
            <el-switch v-model="form.allDay" active-text="全天" inactive-text="按时间" />
          </el-form-item>
          <el-form-item label="提前提醒（分钟）">
            <el-input-number
              v-model="form.remindBeforeMin"
              :min="0"
              :precision="0"
              :controls="false"
              placeholder="不设置提醒"
              class="full-width"
            />
          </el-form-item>
        </div>
        <el-form-item label="地点">
          <el-input v-model="form.location" maxlength="200" placeholder="在哪里？（可选）" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.note"
            type="textarea"
            :rows="3"
            maxlength="1000"
            placeholder="补充需要准备的材料或注意事项（可选）"
          />
        </el-form-item>
        <p v-if="form.remindBeforeMin !== null" class="form-hint">
          保存后由后端每分钟扫描，到点后显示在右上角“通知”中。
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
.event-page {
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
.event-actions .el-button + .el-button,
.filters .el-button + .el-button {
  margin-left: 0;
}

.filter-card {
  margin-bottom: 20px;
  border: none;
  border-radius: 12px;
}

.filters {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) auto auto;
  gap: 12px;
}

.range-filter {
  width: 100%;
}

.filter-hint {
  margin: 10px 0 0;
  color: #909399;
  font-size: 13px;
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

.event-list {
  display: grid;
  gap: 12px;
}

.event-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 22px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: #fff;
}

.event-main {
  min-width: 0;
}

.event-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.event-badges:empty {
  display: none;
}

.event-card h2 {
  overflow-wrap: anywhere;
  font-size: 18px;
  line-height: 1.5;
}

.event-time {
  margin-top: 8px;
  color: #409eff;
  font-size: 14px;
  line-height: 1.6;
}

.event-location {
  margin-top: 6px;
  color: #606266;
  font-size: 14px;
}

.event-note {
  margin-top: 6px;
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
}

.event-actions {
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

@media (max-width: 700px) {
  .event-page {
    padding: 24px 16px 40px;
  }

  .page-header,
  .event-card {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions,
  .event-actions {
    width: 100%;
  }

  .header-actions .el-button,
  .event-actions .el-button {
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
</style>
