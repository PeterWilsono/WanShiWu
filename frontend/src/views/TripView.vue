<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { deleteTrip, listTrips } from '../api/trip'
import { ApiError } from '../api/http'
import AppIcon from '../components/AppIcon.vue'
import TripFormDialog from '../components/TripFormDialog.vue'
import type { Trip } from '../types/trip'
import { formatMoney } from '../utils/money'

const router = useRouter()
const items = ref<Trip[]>([])
const loading = ref(false)
const loadError = ref('')
const dialogVisible = ref(false)
const dialogMode = ref<'manual' | 'ai'>('manual')
const page = ref(1)
const total = ref(0)
const pageSize = 9

function message(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}
async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const result = await listTrips(page.value, pageSize)
    items.value = result.items
    total.value = result.total
  } catch (error) { loadError.value = message(error, '行程加载失败，请稍后重试') }
  finally { loading.value = false }
}
async function remove(trip: Trip): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除“${trip.title}”及全部每日安排吗？`, '删除行程', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch { return }
  try {
    await deleteTrip(trip.id)
    ElMessage.success('行程已删除')
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await load()
  } catch (error) { ElMessage.error(message(error, '删除失败')) }
}
function openDialog(mode: 'manual' | 'ai'): void {
  dialogMode.value = mode
  dialogVisible.value = true
}
function saved(trip: Trip): void { void router.push({ name: 'trip-detail', params: { id: trip.id } }) }
function dateRange(trip: Trip): string {
  if (!trip.start_date) return `${trip.days} 天 · 日期待定`
  return `${trip.start_date} 起 · ${trip.days} 天`
}
onMounted(load)
</script>

<template>
  <main class="trip-page">
    <header class="trip-hero">
      <div><p>JOURNEY NOTES · 旅行规划</p><h1>把远方，写成从容的日常。</h1><span>先留下想去的地方，再慢慢安排每一天。预算与节奏，都清晰可见。</span></div>
      <div class="trip-actions">
        <el-button @click="openDialog('manual')">手动创建</el-button>
        <el-button type="primary" @click="openDialog('ai')"><AppIcon name="sparkle" :size="16" />AI 生成行程</el-button>
      </div>
    </header>
    <el-alert title="可点击右上角“AI 生成行程”创建可编辑草稿；景点、营业时间与价格请出行前核实" type="warning" :closable="false" show-icon class="trip-notice" />
    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false"><el-button size="small" @click="load">重试</el-button></el-alert>
    <section v-loading="loading" class="trip-list" aria-live="polite">
      <el-empty v-if="!loading && !items.length && !loadError" description="还没有旅程，先为一个想去的地方留下计划吧。">
        <div class="empty-actions">
          <el-button @click="openDialog('manual')">手动创建</el-button>
          <el-button type="primary" @click="openDialog('ai')"><AppIcon name="sparkle" :size="16" />AI 生成行程</el-button>
        </div>
      </el-empty>
      <div v-else class="trip-grid">
        <article v-for="trip in items" :key="trip.id" class="trip-card">
          <button class="trip-card__main" @click="router.push({ name: 'trip-detail', params: { id: trip.id } })">
            <span class="trip-card__top"><small>{{ trip.destination }}</small><AppIcon name="transport" :size="23" /></span>
            <span class="trip-card__body"><strong>{{ trip.title }}</strong><span>{{ dateRange(trip) }}</span></span>
            <span class="trip-card__tags"><i>{{ trip.status === 'draft' ? '草稿' : '已确认' }}</i><i v-if="trip.generated_by === 'ai'">AI 辅助</i><i>{{ trip.items.length }} 个安排</i></span>
            <span class="trip-card__budget"><small>预计花费</small><b>{{ formatMoney(trip.planned_cents) }}</b><em v-if="trip.budget_cents !== null" :class="{ over: trip.over_budget }">预算 {{ formatMoney(trip.budget_cents) }}</em></span>
          </button>
          <button class="trip-card__delete" :aria-label="`删除${trip.title}`" @click="remove(trip)">删除</button>
        </article>
      </div>
    </section>
    <el-pagination v-if="total > pageSize" v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="load" />
    <TripFormDialog v-model="dialogVisible" :initial-mode="dialogMode" @saved="saved" />
  </main>
</template>

<style scoped>
.trip-page { width: min(1280px, 100%); margin: 0 auto; padding: 58px 36px 80px; }
.trip-hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 28px; margin-bottom: 28px; }
.trip-hero p { color: var(--vermilion); font-size: 10px; font-weight: 700; letter-spacing: .2em; }
.trip-hero h1 { margin: 14px 0; font-family: var(--font-display); font-size: clamp(36px, 4vw, 52px); font-weight: 500; letter-spacing: -.04em; }
.trip-hero span { color: var(--ink-muted); font-size: 13px; line-height: 1.8; }
.trip-notice { margin-bottom: 24px; }
.trip-actions, .empty-actions { display: flex; align-items: center; justify-content: center; gap: 10px; flex-shrink: 0; }
.trip-actions .el-button, .empty-actions .el-button { display: inline-flex; gap: 6px; margin-left: 0; }
.trip-list { min-height: 300px; }
.trip-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.trip-card { position: relative; overflow: hidden; border: 1px solid var(--line-soft); border-radius: 3px 24px 3px 3px; background: var(--paper-light); transition: transform .25s ease, box-shadow .25s ease; }
.trip-card:hover { box-shadow: var(--shadow-lift); transform: translateY(-4px); }
.trip-card__main { display: flex; width: 100%; min-height: 320px; flex-direction: column; padding: 26px; border: 0; color: var(--ink); background: transparent; cursor: pointer; text-align: left; }
.trip-card__top { display: flex; align-items: center; justify-content: space-between; color: var(--sage); }
.trip-card__top small { font-size: 10px; font-weight: 700; letter-spacing: .18em; }
.trip-card__body { display: grid; gap: 13px; margin: 32px 0 20px; }
.trip-card__body strong { font-family: var(--font-display); font-size: 27px; font-weight: 600; line-height: 1.4; }
.trip-card__body > span { color: var(--ink-muted); font-size: 12px; }
.trip-card__tags { display: flex; flex-wrap: wrap; gap: 7px; }
.trip-card__tags i { padding: 4px 8px; border-radius: 99px; color: var(--ink-secondary); background: var(--paper-deep); font-size: 10px; font-style: normal; }
.trip-card__budget { display: grid; gap: 5px; margin-top: auto; padding-top: 22px; border-top: 1px solid var(--line-soft); }
.trip-card__budget small { color: var(--ink-muted); }
.trip-card__budget b { font-size: 23px; font-weight: 550; }
.trip-card__budget em { color: var(--ink-muted); font-size: 11px; font-style: normal; }
.trip-card__budget em.over { color: var(--vermilion); }
.trip-card__delete { position: absolute; right: 20px; bottom: 20px; padding: 5px; border: 0; color: var(--ink-muted); background: var(--paper-light); cursor: pointer; font-size: 11px; opacity: 0; }
.trip-card:hover .trip-card__delete, .trip-card__delete:focus { opacity: 1; }
.el-pagination { justify-content: center; margin-top: 30px; }
@media (max-width: 1050px) { .trip-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .trip-page { padding: 38px 18px 60px; } .trip-hero { align-items: flex-start; flex-direction: column; } .trip-hero h1 { font-size: 38px; } .trip-grid { grid-template-columns: 1fr; } .trip-card__delete { opacity: 1; } }
</style>
