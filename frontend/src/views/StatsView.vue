<script setup lang="ts">
import type { EChartsCoreOption } from 'echarts/core'
import { computed, onMounted, ref } from 'vue'

import { ApiError } from '../api/http'
import { getDailyStats, getMonthlyStats } from '../api/stats'
import EChart from '../components/EChart.vue'
import { useAuthStore } from '../stores/auth'
import type { DailyStats, MonthlyStats } from '../types/stats'
import { formatMoney } from '../utils/money'
import { monthInputFor } from '../utils/time'

const authStore = useAuthStore()
const timeZone = computed(() => authStore.user?.timezone || 'Asia/Shanghai')
const month = ref(monthInputFor(new Date().toISOString(), timeZone.value))
const monthly = ref<MonthlyStats>(emptyMonthly(month.value))
const daily = ref<DailyStats>({ month: month.value, days: [] })
const loading = ref(false)
const loadError = ref('')

function emptyMonthly(value: string): MonthlyStats {
  return { month: value, income_cents: 0, expense_cents: 0, balance_cents: 0, categories: [] }
}

async function loadStats(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const [monthlyResult, dailyResult] = await Promise.all([
      getMonthlyStats(month.value),
      getDailyStats(month.value),
    ])
    monthly.value = monthlyResult
    daily.value = dailyResult
  } catch (error) {
    loadError.value = error instanceof ApiError ? error.message : '统计加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const expenseCategories = computed(() =>
  monthly.value.categories.filter((item) => item.type === 'expense'),
)

const pieOption = computed<EChartsCoreOption>(() => ({
  color: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#9b59b6', '#36a3a3', '#c45656'],
  tooltip: {
    trigger: 'item',
    confine: true,
    formatter: (params: unknown) => {
      const item = params as { name: string; value: number; percent: number }
      return `${item.name}<br/>${formatMoney(item.value)}（${item.percent}%）`
    },
  },
  legend: { bottom: 0, type: 'scroll' },
  series: [{
    name: '支出分类',
    type: 'pie',
    radius: ['38%', '65%'],
    center: ['50%', '44%'],
    label: { formatter: '{b}\n{d}%' },
    data: expenseCategories.value.map((item) => ({
      name: item.category_name,
      value: item.amount_cents,
    })),
  }],
}))

const lineOption = computed<EChartsCoreOption>(() => ({
  color: ['#409eff'],
  tooltip: {
    trigger: 'axis',
    confine: true,
    formatter: (params: unknown) => {
      const item = (params as Array<{ axisValue: string; value: number }>)[0]
      return item ? `${item.axisValue}<br/>支出 ${formatMoney(item.value)}` : ''
    },
  },
  grid: { left: 72, right: 24, top: 28, bottom: 44 },
  xAxis: {
    type: 'category',
    data: daily.value.days.map((item) => item.date),
    axisLabel: { formatter: (value: string) => value.slice(5), interval: 2 },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    axisLabel: { formatter: (value: number) => formatMoney(value, false) },
  },
  series: [{
    name: '每日支出',
    type: 'line',
    smooth: true,
    symbolSize: 6,
    areaStyle: { opacity: 0.1 },
    data: daily.value.days.map((item) => item.expense_cents),
  }],
}))

onMounted(loadStats)
</script>

<template>
  <main class="stats-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">生活管家</p>
        <h1>月度统计</h1>
        <p class="page-subtitle">按你的时区汇总收支，看看钱主要花在了哪里。</p>
      </div>
      <div class="header-actions">
        <el-date-picker
          v-model="month"
          type="month"
          value-format="YYYY-MM"
          :clearable="false"
          aria-label="统计月份"
          @change="loadStats"
        />
        <el-button @click="$router.push({ name: 'transactions' })">查看账目</el-button>
        <el-button @click="$router.push({ name: 'home' })">返回首页</el-button>
      </div>
    </header>

    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false">
      <el-button size="small" @click="loadStats">重新加载</el-button>
    </el-alert>

    <div v-loading="loading" class="stats-content" aria-live="polite">
      <section class="summary-grid" aria-label="本月收支总览">
        <el-card shadow="never" class="summary-card">
          <span>本月收入</span><strong class="income">{{ formatMoney(monthly.income_cents) }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span>本月支出</span><strong>{{ formatMoney(monthly.expense_cents) }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span>本月结余</span>
          <strong :class="{ negative: monthly.balance_cents < 0 }">
            {{ formatMoney(monthly.balance_cents) }}
          </strong>
        </el-card>
      </section>

      <section class="chart-grid">
        <el-card shadow="never">
          <template #header><strong>支出分类占比</strong></template>
          <EChart
            v-if="expenseCategories.length"
            :option="pieOption"
            label="本月支出分类占比饼图"
          />
          <el-empty v-else description="本月暂无支出分类数据" />
        </el-card>
        <el-card shadow="never" class="daily-card">
          <template #header><strong>每日支出</strong></template>
          <EChart v-if="daily.days.length" :option="lineOption" label="本月每日支出折线图" />
          <el-empty v-else description="暂无每日支出数据" />
        </el-card>
      </section>
    </div>
  </main>
</template>

<style scoped>
.stats-page { width: min(1180px, 100%); margin: 0 auto; padding: 40px 24px 56px; }
.page-header { display: flex; justify-content: space-between; gap: 24px; margin-bottom: 28px; }
.page-eyebrow { margin-bottom: 6px; color: #409eff; font-size: 13px; font-weight: 600; }
.page-header h1 { margin-bottom: 8px; font-size: 32px; }
.page-subtitle { color: #909399; line-height: 1.6; }
.header-actions { display: flex; align-items: flex-start; flex-shrink: 0; gap: 10px; }
.header-actions .el-button + .el-button { margin-left: 0; }
.el-alert { margin-bottom: 16px; }
.stats-content { min-height: 300px; }
.summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }
.summary-card :deep(.el-card__body) { display: flex; flex-direction: column; gap: 10px; }
.summary-card span { color: #909399; font-size: 14px; }
.summary-card strong { font-size: 28px; }
.summary-card .income { color: #d03050; }
.summary-card .negative { color: #67c23a; }
.chart-grid { display: grid; grid-template-columns: minmax(300px, 0.8fr) minmax(480px, 1.2fr); gap: 16px; }
@media (max-width: 950px) {
  .page-header { flex-direction: column; }
  .chart-grid { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
  .stats-page { padding: 24px 16px 40px; }
  .header-actions { flex-wrap: wrap; }
  .header-actions .el-date-editor { width: 100%; }
  .summary-grid { grid-template-columns: 1fr; }
  .summary-card strong { font-size: 24px; }
}
</style>
