<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  addTripItem, deleteTripItem, exportTripMarkdown, getTrip, reorderTripItems, updateTrip, updateTripItem,
} from '../api/trip'
import { ApiError } from '../api/http'
import type { Trip, TripItem } from '../types/trip'
import { centsToYuanInput, formatMoney } from '../utils/money'

const route = useRoute()
const router = useRouter()
const tripId = Number(route.params.id)
const trip = ref<Trip | null>(null)
const loading = ref(false)
const loadError = ref('')
const reordering = ref(false)
const exporting = ref(false)
const savingItem = ref(false)
const savingTrip = ref(false)
const draggedId = ref<number | null>(null)
const dragOverDay = ref<number | null>(null)
const itemVisible = ref(false)
const tripVisible = ref(false)
const editingItemId = ref<number | null>(null)
const itemForm = ref({ dayIndex: 1, startTime: '', place: '', note: '', cost: '0' })
const tripForm = ref({ title: '', destination: '', startDate: '', days: 1, budget: '', preferences: '', status: 'draft' as 'draft' | 'confirmed' })

const budgetPercent = computed(() => {
  if (!trip.value?.budget_cents) return 0
  return Math.min(100, Math.round(trip.value.planned_cents / trip.value.budget_cents * 100))
})
function message(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}
async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try { trip.value = await getTrip(tripId) }
  catch (error) { loadError.value = message(error, '行程加载失败或不存在') }
  finally { loading.value = false }
}
function moneyToCents(value: string): number {
  const normalized = value.trim()
  if (!/^(0|[1-9]\d*)(?:\.\d{1,2})?$/.test(normalized)) throw new Error('费用需为非负数字，最多两位小数')
  const cents = Math.round(Number(normalized) * 100)
  if (!Number.isSafeInteger(cents) || cents > 9_999_999_999) throw new Error('费用超出可支持的范围')
  return cents
}
function openItem(day: number, item?: TripItem): void {
  editingItemId.value = item?.id ?? null
  itemForm.value = {
    dayIndex: item?.day_index ?? day,
    startTime: item?.start_time?.slice(0, 5) ?? '',
    place: item?.place ?? '',
    note: item?.note ?? '',
    cost: centsToYuanInput(item?.cost_cents ?? 0),
  }
  itemVisible.value = true
}
async function saveItem(): Promise<void> {
  if (!itemForm.value.place.trim()) { ElMessage.warning('请填写地点或安排'); return }
  savingItem.value = true
  try {
    const payload = {
      day_index: itemForm.value.dayIndex,
      start_time: itemForm.value.startTime || null,
      place: itemForm.value.place.trim(),
      note: itemForm.value.note.trim() || null,
      cost_cents: moneyToCents(itemForm.value.cost),
    }
    if (editingItemId.value) await updateTripItem(tripId, editingItemId.value, payload)
    else await addTripItem(tripId, payload)
    itemVisible.value = false
    ElMessage.success(editingItemId.value ? '安排已更新' : '安排已添加')
    await load()
  } catch (error) { ElMessage.error(message(error, error instanceof Error ? error.message : '保存失败')) }
  finally { savingItem.value = false }
}
async function removeItem(item: TripItem): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除“${item.place}”吗？`, '删除安排', { type: 'warning' })
  } catch { return }
  try { await deleteTripItem(tripId, item.id); ElMessage.success('安排已删除'); await load() }
  catch (error) { ElMessage.error(message(error, '删除失败')) }
}
function openTripEdit(): void {
  if (!trip.value) return
  tripForm.value = {
    title: trip.value.title,
    destination: trip.value.destination,
    startDate: trip.value.start_date ?? '',
    days: trip.value.days,
    budget: trip.value.budget_cents === null ? '' : centsToYuanInput(trip.value.budget_cents),
    preferences: trip.value.preferences ?? '',
    status: trip.value.status,
  }
  tripVisible.value = true
}
async function saveTrip(): Promise<void> {
  savingTrip.value = true
  try {
    const budget = tripForm.value.budget.trim()
    if (budget) moneyToCents(budget)
    if (!tripForm.value.title.trim() || !tripForm.value.destination.trim()) throw new Error('标题与目的地不能为空')
    await updateTrip(tripId, {
      title: tripForm.value.title.trim(), destination: tripForm.value.destination.trim(),
      start_date: tripForm.value.startDate || null, days: tripForm.value.days,
      budget_cents: budget ? moneyToCents(budget) : null,
      preferences: tripForm.value.preferences.trim() || null, status: tripForm.value.status,
    })
    tripVisible.value = false
    ElMessage.success('行程信息已更新')
    await load()
  } catch (error) { ElMessage.error(message(error, error instanceof Error ? error.message : '保存失败')) }
  finally { savingTrip.value = false }
}
function startDrag(item: TripItem, event: DragEvent): void {
  draggedId.value = item.id
  if (event.dataTransfer) { event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData('text/plain', String(item.id)) }
}
async function moveToDay(day: number, target?: TripItem): Promise<void> {
  if (!trip.value || draggedId.value === null || draggedId.value === target?.id) return
  const dragged = trip.value.items.find((item) => item.id === draggedId.value)
  if (!dragged) return
  const groups = new Map<number, TripItem[]>()
  for (let index = 1; index <= trip.value.days; index += 1) {
    groups.set(index, trip.value.daily_summaries[index - 1].items.filter((item) => item.id !== dragged.id))
  }
  const destination = groups.get(day) ?? []
  const insertAt = target ? destination.findIndex((item) => item.id === target.id) : destination.length
  destination.splice(insertAt < 0 ? destination.length : insertAt, 0, { ...dragged, day_index: day })
  groups.set(day, destination)
  const reordered = Array.from(groups.values()).flatMap((items) => items.map((item, sortOrder) => ({
    id: item.id, day_index: item.day_index, sort_order: sortOrder,
  })))
  reordering.value = true
  try { trip.value = await reorderTripItems(tripId, reordered); ElMessage.success('顺序已更新') }
  catch (error) { ElMessage.error(message(error, '排序失败，已恢复原顺序')); await load() }
  finally { reordering.value = false; draggedId.value = null; dragOverDay.value = null }
}
function moveWithinDay(item: TripItem, direction: number): void {
  if (!trip.value) return
  const siblings = trip.value.daily_summaries[item.day_index - 1].items
  const target = siblings[siblings.indexOf(item) + direction]
  if (!target) return
  draggedId.value = item.id
  const reorderedTarget = direction > 0
    ? siblings[siblings.indexOf(target) + 1]
    : target
  void moveToDay(item.day_index, reorderedTarget)
}
async function exportMarkdown(): Promise<void> {
  if (!trip.value) return
  exporting.value = true
  try {
    const blob = await exportTripMarkdown(tripId)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${trip.value.title}.md`
    anchor.click()
    URL.revokeObjectURL(url)
    ElMessage.success('Markdown 已导出')
  } catch (error) { ElMessage.error(message(error, '导出失败')) }
  finally { exporting.value = false }
}
onMounted(load)
</script>

<template>
  <main class="trip-detail" v-loading="loading">
    <el-alert v-if="loadError" :title="loadError" type="error" :closable="false" show-icon>
      <el-button size="small" @click="load">重试</el-button><el-button size="small" text @click="router.push({ name: 'trip' })">返回列表</el-button>
    </el-alert>
    <template v-if="trip">
      <button class="back-link" @click="router.push({ name: 'trip' })">← 返回旅行手帖</button>
      <header class="detail-hero">
        <div><p>{{ trip.destination }} · {{ trip.generated_by === 'ai' ? 'AI 辅助草稿' : '手动规划' }}</p><h1>{{ trip.title }}</h1><span>{{ trip.start_date || '日期待定' }} · {{ trip.days }} 天 · {{ trip.status === 'draft' ? '草稿' : '已确认' }}</span></div>
        <div class="detail-actions"><el-button :loading="exporting" @click="exportMarkdown">导出 Markdown</el-button><el-button type="primary" @click="openTripEdit">编辑行程</el-button></div>
      </header>
      <el-alert title="AI 生成，景点、营业时间与价格请出行前核实" type="warning" :closable="false" show-icon />
      <section class="budget-panel" aria-label="预算概览">
        <div><small>预计总花费</small><strong>{{ formatMoney(trip.planned_cents) }}</strong></div>
        <div><small>总预算</small><strong>{{ trip.budget_cents === null ? '未设置' : formatMoney(trip.budget_cents) }}</strong></div>
        <div><small>预算余额</small><strong :class="{ over: trip.over_budget }">{{ trip.budget_remaining_cents === null ? '—' : formatMoney(trip.budget_remaining_cents) }}</strong></div>
        <el-progress v-if="trip.budget_cents !== null" :percentage="budgetPercent" :status="trip.over_budget ? 'exception' : undefined" :show-text="false" />
      </section>
      <p v-if="trip.preferences" class="preferences">旅行偏好：{{ trip.preferences }}</p>
      <div class="reorder-tip">可拖动安排到其他位置或另一天，也可使用条目内的上移、下移按钮。</div>
      <section class="days-grid" :class="{ busy: reordering }">
        <article v-for="day in trip.daily_summaries" :key="day.day_index" class="day-column" :class="{ over: dragOverDay === day.day_index }" @dragover.prevent="dragOverDay = day.day_index" @dragleave="dragOverDay = null" @drop="moveToDay(day.day_index)">
          <header><div><small>DAY {{ String(day.day_index).padStart(2, '0') }}</small><h2>第 {{ day.day_index }} 天</h2><span>{{ day.date || '日期待定' }}</span></div><el-button circle size="small" :aria-label="`第${day.day_index}天添加安排`" @click="openItem(day.day_index)">＋</el-button></header>
          <div class="day-items">
            <section v-for="(item, index) in day.items" :key="item.id" class="plan-item" draggable="true" @dragstart="startDrag(item, $event)" @dragend="draggedId = null; dragOverDay = null" @dragover.prevent.stop @drop.stop="moveToDay(day.day_index, item)">
              <div class="plan-item__top"><time>{{ item.start_time?.slice(0, 5) || '时间自由' }}</time><span class="drag-handle">⠿</span></div>
              <h3>{{ item.place }}</h3><p v-if="item.note">{{ item.note }}</p><strong>{{ formatMoney(item.cost_cents) }}</strong>
              <div class="plan-item__actions"><button :disabled="index === 0" @click="moveWithinDay(item, -1)">上移</button><button :disabled="index === day.items.length - 1" @click="moveWithinDay(item, 1)">下移</button><button @click="openItem(day.day_index, item)">编辑</button><button @click="removeItem(item)">删除</button></div>
            </section>
            <button v-if="!day.items.length" class="empty-day" @click="openItem(day.day_index)">为这一天添加第一个安排</button>
          </div>
          <footer>当日小计 <strong>{{ formatMoney(day.subtotal_cents) }}</strong></footer>
        </article>
      </section>
    </template>

    <el-dialog v-model="itemVisible" :title="editingItemId ? '编辑每日安排' : '添加每日安排'" width="min(560px, 94vw)">
      <el-form label-position="top"><div class="item-form-grid"><el-form-item label="第几天"><el-input-number v-model="itemForm.dayIndex" :min="1" :max="trip?.days || 1" class="full-width" /></el-form-item><el-form-item label="开始时间"><el-time-select v-model="itemForm.startTime" start="00:00" end="23:30" step="00:30" class="full-width" /></el-form-item></div><el-form-item label="地点或安排" required><el-input v-model="itemForm.place" maxlength="200" /></el-form-item><el-form-item label="预计费用（元）"><el-input v-model="itemForm.cost" /></el-form-item><el-form-item label="备注"><el-input v-model="itemForm.note" type="textarea" :rows="3" maxlength="2000" /></el-form-item></el-form>
      <template #footer><el-button @click="itemVisible = false">取消</el-button><el-button type="primary" :loading="savingItem" @click="saveItem">保存安排</el-button></template>
    </el-dialog>
    <el-dialog v-model="tripVisible" title="编辑行程信息" width="min(620px, 94vw)">
      <el-form label-position="top"><el-form-item label="标题" required><el-input v-model="tripForm.title" maxlength="100" /></el-form-item><div class="item-form-grid"><el-form-item label="目的地" required><el-input v-model="tripForm.destination" maxlength="100" /></el-form-item><el-form-item label="出发日期"><el-date-picker v-model="tripForm.startDate" type="date" value-format="YYYY-MM-DD" class="full-width" /></el-form-item><el-form-item label="天数"><el-input-number v-model="tripForm.days" :min="1" :max="30" class="full-width" /></el-form-item><el-form-item label="总预算（元）"><el-input v-model="tripForm.budget" placeholder="留空表示不设预算" /></el-form-item></div><el-form-item label="状态"><el-radio-group v-model="tripForm.status"><el-radio-button value="draft">草稿</el-radio-button><el-radio-button value="confirmed">已确认</el-radio-button></el-radio-group></el-form-item><el-form-item label="旅行偏好"><el-input v-model="tripForm.preferences" type="textarea" :rows="3" maxlength="1000" /></el-form-item></el-form>
      <template #footer><el-button @click="tripVisible = false">取消</el-button><el-button type="primary" :loading="savingTrip" @click="saveTrip">保存修改</el-button></template>
    </el-dialog>
  </main>
</template>

<style scoped>
.trip-detail { width: min(1400px, 100%); min-height: 60vh; margin: 0 auto; padding: 40px 36px 80px; }
.back-link { padding: 0; border: 0; color: var(--ink-muted); background: transparent; cursor: pointer; }
.detail-hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin: 30px 0 24px; }
.detail-hero p { color: var(--vermilion); font-size: 10px; font-weight: 700; letter-spacing: .18em; }
.detail-hero h1 { margin: 12px 0; font-family: var(--font-display); font-size: clamp(38px, 4vw, 54px); font-weight: 500; }
.detail-hero span { color: var(--ink-muted); font-size: 13px; }
.budget-panel { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin: 22px 0; padding: 25px 30px; border: 1px solid var(--line-soft); border-radius: 4px 20px 4px 4px; background: var(--paper-light); }
.budget-panel > div { display: grid; gap: 8px; }.budget-panel small { color: var(--ink-muted); }.budget-panel strong { font-size: 24px; font-weight: 550; }.budget-panel strong.over { color: var(--vermilion); }.budget-panel .el-progress { grid-column: 1 / -1; }
.preferences, .reorder-tip { color: var(--ink-muted); font-size: 12px; line-height: 1.8; }.reorder-tip { margin: 22px 0 12px; }
.days-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); align-items: start; gap: 16px; transition: opacity .2s; }.days-grid.busy { pointer-events: none; opacity: .6; }
.day-column { overflow: hidden; border: 1px solid var(--line-soft); border-radius: 3px 18px 3px 3px; background: var(--paper-light); transition: border-color .2s; }.day-column.over { border-color: var(--vermilion); }
.day-column > header { display: flex; align-items: center; justify-content: space-between; padding: 20px; border-bottom: 1px solid var(--line-soft); }.day-column header small { color: var(--vermilion); font-size: 9px; letter-spacing: .18em; }.day-column h2 { margin: 6px 0; font-family: var(--font-display); font-size: 22px; }.day-column header span { color: var(--ink-muted); font-size: 11px; }
.day-items { min-height: 80px; padding: 12px; }.plan-item { margin-bottom: 10px; padding: 16px; border: 1px solid var(--line-soft); border-radius: 3px 12px 3px 3px; background: var(--paper); cursor: grab; }.plan-item:active { cursor: grabbing; }.plan-item__top { display: flex; justify-content: space-between; color: var(--sage); }.plan-item time { font-size: 12px; font-weight: 700; }.drag-handle { color: var(--ink-muted); }.plan-item h3 { margin: 10px 0; font-family: var(--font-display); font-size: 18px; }.plan-item p { color: var(--ink-muted); font-size: 12px; line-height: 1.7; white-space: pre-wrap; }.plan-item > strong { display: block; margin-top: 10px; font-size: 13px; }.plan-item__actions { display: flex; gap: 10px; margin-top: 12px; }.plan-item__actions button { padding: 0; border: 0; color: var(--ink-muted); background: transparent; cursor: pointer; font-size: 11px; }.plan-item__actions button:hover { color: var(--vermilion); }.plan-item__actions button:disabled { cursor: default; opacity: .3; }
.empty-day { width: 100%; padding: 25px 10px; border: 1px dashed var(--line); color: var(--ink-muted); background: transparent; cursor: pointer; font-size: 12px; }.day-column > footer { display: flex; justify-content: space-between; padding: 16px 20px; border-top: 1px solid var(--line-soft); color: var(--ink-muted); font-size: 12px; }.day-column footer strong { color: var(--ink); }
.item-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }.full-width { width: 100%; }
@media (max-width: 640px) { .trip-detail { padding: 30px 18px 60px; }.detail-hero { align-items: flex-start; flex-direction: column; }.detail-actions { display: flex; width: 100%; }.detail-actions .el-button { flex: 1; }.budget-panel { grid-template-columns: 1fr; padding: 20px; }.days-grid { grid-template-columns: 1fr; }.item-form-grid { grid-template-columns: 1fr; gap: 0; } }
</style>
