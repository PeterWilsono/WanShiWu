<script setup lang="ts">
import type {
  CalendarOptions,
  EventClickArg,
  EventInput,
  EventSourceFuncArg,
} from '@fullcalendar/core'
import zhCnLocale from '@fullcalendar/core/locales/zh-cn'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import FullCalendar from '@fullcalendar/vue3'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { listEvents } from '../api/events'
import { ApiError } from '../api/http'
import { listTodos } from '../api/todos'
import { useAuthStore } from '../stores/auth'
import type { Event as LifeEvent } from '../types/event'
import type { Todo, TodoStatus } from '../types/todo'
import { formatDateTime } from '../utils/time'

interface CalendarDetails {
  kind: 'event' | 'todo'
  title: string
  startAt: string
  endAt: string | null
  location: string | null
  note: string | null
  status: TodoStatus | null
  priority: number | null
}

const router = useRouter()
const authStore = useAuthStore()
const timeZone = computed(() => authStore.user?.timezone || 'Asia/Shanghai')
const calendarRef = ref<InstanceType<typeof FullCalendar> | null>(null)
const loading = ref(false)
const loadError = ref('')
const loadWarning = ref('')
const selected = ref<CalendarDetails | null>(null)
const dialogVisible = ref(false)
const statusLabels: Record<TodoStatus, string> = {
  pending: '进行中',
  done: '已完成',
  cancelled: '已取消',
}

function eventInput(event: LifeEvent): EventInput {
  return {
    id: `event-${event.id}`,
    title: event.title,
    start: event.start_at,
    end: event.end_at || undefined,
    allDay: event.all_day,
    color: '#409eff',
    extendedProps: {
      details: {
        kind: 'event', title: event.title, startAt: event.start_at, endAt: event.end_at,
        location: event.location, note: event.note, status: null, priority: null,
      } satisfies CalendarDetails,
    },
  }
}

function todoInput(todo: Todo): EventInput | null {
  if (!todo.due_at) return null
  return {
    id: `todo-${todo.id}`,
    title: `待办：${todo.title}`,
    start: todo.due_at,
    color: '#e6a23c',
    classNames: ['calendar-todo', `todo-${todo.status}`],
    extendedProps: {
      details: {
        kind: 'todo', title: todo.title, startAt: todo.due_at, endAt: null,
        location: null, note: todo.note, status: todo.status, priority: todo.priority,
      } satisfies CalendarDetails,
    },
  }
}

async function fetchEntries(
  fetchInfo: EventSourceFuncArg,
  success: (entries: EventInput[]) => void,
): Promise<void> {
  loading.value = true
  loadError.value = ''
  loadWarning.value = ''
  const rangeStart = fetchInfo.start.toISOString()
  // FullCalendar 的 end 不包含在视图内，现有后端查询则包含 range_end。
  const rangeEnd = new Date(fetchInfo.end.getTime() - 1).toISOString()
  try {
    const [events, todos] = await Promise.all([
      listEvents({ range_start: rangeStart, range_end: rangeEnd, page_size: 100 }),
      listTodos({
        due_after: rangeStart, due_before: rangeEnd, sort: 'due_at', order: 'asc', page_size: 100,
      }),
    ])
    if (events.total > events.items.length || todos.total > todos.items.length) {
      loadWarning.value = '当前日期范围数据超过 100 条，仅显示已加载内容，可前往管理页分页查看。'
    }
    success([
      ...events.items.map(eventInput),
      ...todos.items.map(todoInput).filter((item) => item !== null),
    ])
  } catch (error) {
    loadError.value = error instanceof ApiError ? error.message : '日历加载失败，请稍后重试'
    success([])
  } finally {
    loading.value = false
  }
}

function showDetails(clickInfo: EventClickArg): void {
  selected.value = clickInfo.event.extendedProps.details as CalendarDetails
  dialogVisible.value = true
}

function refetch(): void {
  calendarRef.value?.getApi().refetchEvents()
}

function openManager(): void {
  if (!selected.value) return
  void router.push({ name: selected.value.kind === 'event' ? 'events' : 'todos' })
}

const calendarOptions: CalendarOptions = {
  plugins: [dayGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  locale: zhCnLocale,
  timeZone: timeZone.value,
  height: 'auto',
  fixedWeekCount: false,
  dayMaxEventRows: 3,
  moreLinkClick: 'popover',
  displayEventTime: true,
  eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
  events: fetchEntries,
  eventClick: showDetails,
}
</script>

<template>
  <main class="calendar-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">生活管家</p>
        <h1>月历</h1>
        <p class="page-subtitle">蓝色为日程，橙色为有截止时间的待办；点击条目可查看详情。</p>
      </div>
      <div class="header-actions">
        <el-button @click="$router.push({ name: 'events' })">管理日程</el-button>
        <el-button @click="$router.push({ name: 'todos' })">管理待办</el-button>
        <el-button @click="$router.push({ name: 'home' })">返回首页</el-button>
      </div>
    </header>

    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false">
      <el-button size="small" @click="refetch">重新加载</el-button>
    </el-alert>
    <el-alert v-if="loadWarning" :title="loadWarning" type="warning" show-icon :closable="false" />
    <section v-loading="loading" class="calendar-card">
      <FullCalendar ref="calendarRef" :options="calendarOptions" />
    </section>

    <el-dialog v-model="dialogVisible" :title="selected?.kind === 'event' ? '日程详情' : '待办详情'" width="min(480px, 92vw)">
      <el-descriptions v-if="selected" :column="1" border>
        <el-descriptions-item label="标题">{{ selected.title }}</el-descriptions-item>
        <el-descriptions-item :label="selected.kind === 'event' ? '开始时间' : '截止时间'">
          {{ formatDateTime(selected.startAt, timeZone) }}
        </el-descriptions-item>
        <el-descriptions-item v-if="selected.endAt" label="结束时间">
          {{ formatDateTime(selected.endAt, timeZone) }}
        </el-descriptions-item>
        <el-descriptions-item v-if="selected.location" label="地点">{{ selected.location }}</el-descriptions-item>
        <el-descriptions-item v-if="selected.status" label="状态">
          {{ statusLabels[selected.status] }}
        </el-descriptions-item>
        <el-descriptions-item v-if="selected.priority" label="优先级">{{ selected.priority }} 级</el-descriptions-item>
        <el-descriptions-item label="备注">{{ selected.note || '无' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer><el-button type="primary" @click="openManager">前往管理</el-button></template>
    </el-dialog>
  </main>
</template>

<style scoped>
.calendar-page { width: min(1180px, 100%); margin: 0 auto; padding: 40px 24px 56px; }
.page-header { display: flex; justify-content: space-between; gap: 24px; margin-bottom: 28px; }
.page-eyebrow { margin-bottom: 6px; color: #409eff; font-size: 13px; font-weight: 600; }
.page-header h1 { margin-bottom: 8px; font-size: 32px; }
.page-subtitle { color: #909399; line-height: 1.6; }
.header-actions { display: flex; flex-shrink: 0; gap: 10px; }
.header-actions .el-button + .el-button { margin-left: 0; }
.el-alert { margin-bottom: 16px; }
.calendar-card { min-height: 480px; padding: 18px; background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; }
.calendar-card :deep(.fc) { --fc-border-color: #e4e7ed; --fc-button-bg-color: #409eff; --fc-button-border-color: #409eff; --fc-today-bg-color: #ecf5ff; }
.calendar-card :deep(.fc-event) { cursor: pointer; }
.calendar-card :deep(.todo-done) { opacity: 0.6; }
.calendar-card :deep(.todo-cancelled) { opacity: 0.5; text-decoration: line-through; }
@media (max-width: 800px) {
  .page-header { flex-direction: column; }
  .header-actions { flex-wrap: wrap; }
}
@media (max-width: 700px) {
  .calendar-page { padding: 24px 10px 40px; }
  .calendar-card { padding: 8px 2px; }
  .calendar-card :deep(.fc-toolbar) { flex-wrap: wrap; gap: 10px; }
  .calendar-card :deep(.fc-toolbar-title) { font-size: 20px; }
  .calendar-card :deep(.fc-daygrid-day-number), .calendar-card :deep(.fc-col-header-cell-cushion) { font-size: 12px; }
}
</style>
