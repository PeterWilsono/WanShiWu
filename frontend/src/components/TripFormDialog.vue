<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, ref, watch } from 'vue'

import { createTrip, generateTrip } from '../api/trip'
import { ApiError } from '../api/http'
import type { Trip, TripDraft, TripItemPayload } from '../types/trip'
import { centsToYuanInput, formatMoney } from '../utils/money'

interface EditorItem extends TripItemPayload { cost: string }

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [trip: Trip]
}>()
const visible = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
const mode = ref<'manual' | 'ai'>('manual')
const form = ref({ title: '', destination: '', startDate: '', days: 3, budget: '', preferences: '' })
const generating = ref(false)
const saving = ref(false)
const draft = ref<TripDraft | null>(null)
const draftTitle = ref('')
const editorItems = ref<EditorItem[]>([])

watch(visible, (open) => {
  if (!open) return
  mode.value = 'manual'
  form.value = { title: '', destination: '', startDate: '', days: 3, budget: '', preferences: '' }
  draft.value = null
  editorItems.value = []
})

function moneyToCents(value: string, allowEmpty = false): number | null {
  const normalized = value.trim()
  if (allowEmpty && !normalized) return null
  if (!/^(0|[1-9]\d*)(?:\.\d{1,2})?$/.test(normalized)) throw new Error('金额需为非负数字，最多两位小数')
  const cents = Math.round(Number(normalized) * 100)
  if (!Number.isSafeInteger(cents) || cents > 9_999_999_999) throw new Error('金额超出可支持的范围')
  return cents
}

function requestData() {
  if (!form.value.destination.trim()) throw new Error('请填写目的地')
  return {
    destination: form.value.destination.trim(),
    start_date: form.value.startDate || null,
    days: form.value.days,
    budget_cents: moneyToCents(form.value.budget, true),
    preferences: form.value.preferences.trim() || null,
  }
}

async function generate(): Promise<void> {
  generating.value = true
  try {
    draft.value = await generateTrip(requestData())
    draftTitle.value = draft.value.draft.title
    editorItems.value = draft.value.draft.items.map((item) => ({
      ...item,
      cost: centsToYuanInput(item.cost_cents ?? 0),
      start_time: item.start_time?.slice(0, 5) || '',
      note: item.note || '',
    }))
    ElMessage.success('草稿已生成，请检查后保存')
  } catch (error) {
    ElMessage.error(error instanceof ApiError || error instanceof Error ? error.message : '生成失败')
  } finally { generating.value = false }
}

const groupedItems = computed(() => Array.from({ length: form.value.days }, (_, index) => ({
  day: index + 1,
  items: editorItems.value.filter((item) => item.day_index === index + 1),
})))
const previewPlanned = computed(() => editorItems.value.reduce((sum, item) => {
  try { return sum + (moneyToCents(item.cost) ?? 0) } catch { return sum }
}, 0))

function toPayloadItems(): TripItemPayload[] {
  return editorItems.value.map((item, index) => {
    if (!item.place.trim()) throw new Error(`第 ${index + 1} 个条目缺少地点`)
    return {
      day_index: item.day_index,
      sort_order: item.sort_order,
      start_time: item.start_time || null,
      place: item.place.trim(),
      note: item.note?.trim() || null,
      cost_cents: moneyToCents(item.cost) ?? 0,
    }
  })
}

async function save(): Promise<void> {
  saving.value = true
  try {
    if (mode.value === 'manual' && !form.value.title.trim()) throw new Error('请填写行程标题')
    const common = requestData()
    const payload = mode.value === 'manual'
      ? { ...common, title: form.value.title.trim(), status: 'draft' as const, items: [] }
      : {
          ...common,
          title: draftTitle.value.trim(),
          generated_by: 'ai' as const,
          status: 'draft' as const,
          items: toPayloadItems(),
        }
    if (!payload.title) throw new Error('行程标题不能为空')
    const trip = await createTrip(payload)
    ElMessage.success('行程已保存')
    emit('saved', trip)
    visible.value = false
  } catch (error) {
    ElMessage.error(error instanceof ApiError || error instanceof Error ? error.message : '保存失败')
  } finally { saving.value = false }
}
</script>

<template>
  <el-dialog v-model="visible" title="规划一段旅程" width="min(920px, 94vw)" top="4vh">
    <el-radio-group v-model="mode" @change="draft = null">
      <el-radio-button value="manual">手动创建</el-radio-button>
      <el-radio-button value="ai">AI 生成草稿</el-radio-button>
    </el-radio-group>
    <el-form label-position="top" class="trip-create-form" @submit.prevent>
      <el-form-item v-if="mode === 'manual'" label="行程标题" required>
        <el-input v-model="form.title" maxlength="100" placeholder="例如：京都五日慢行" />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="目的地" required><el-input v-model="form.destination" maxlength="100" placeholder="城市或地区" /></el-form-item>
        <el-form-item label="出发日期"><el-date-picker v-model="form.startDate" type="date" value-format="YYYY-MM-DD" class="full-width" /></el-form-item>
        <el-form-item label="天数" required><el-input-number v-model="form.days" :min="1" :max="30" class="full-width" /></el-form-item>
        <el-form-item label="总预算（元，可留空）"><el-input v-model="form.budget" placeholder="例如 3000.00" /></el-form-item>
      </div>
      <el-form-item label="旅行偏好"><el-input v-model="form.preferences" type="textarea" :rows="2" maxlength="1000" placeholder="例如：少走路，偏爱博物馆和当地食物" /></el-form-item>
    </el-form>

    <div v-if="mode === 'ai' && !draft" class="generate-panel">
      <p>AI 只生成候选安排，确认保存前不会写入行程。</p>
      <el-button type="primary" :loading="generating" @click="generate">{{ generating ? '正在规划…' : '生成可编辑草稿' }}</el-button>
    </div>
    <section v-if="mode === 'ai' && draft" class="draft-preview">
      <el-alert title="AI 生成，景点、营业时间与价格请出行前核实" type="warning" :closable="false" show-icon />
      <el-input v-model="draftTitle" maxlength="100" class="draft-title" aria-label="草稿标题" />
      <div v-for="group in groupedItems" :key="group.day" class="draft-day">
        <h3>第 {{ group.day }} 天</h3>
        <div v-for="(item, itemIndex) in group.items" :key="`${group.day}-${itemIndex}`" class="draft-item">
          <el-input-number v-model="item.day_index" :min="1" :max="form.days" aria-label="所属日期" />
          <el-time-select v-model="item.start_time" start="06:00" end="23:30" step="00:30" placeholder="时间" />
          <el-input v-model="item.place" maxlength="200" placeholder="地点" />
          <el-input v-model="item.cost" class="cost-input" aria-label="预计费用（元）" />
          <el-input v-model="item.note" maxlength="2000" placeholder="安排备注" class="draft-note" />
          <el-button text type="danger" @click="editorItems.splice(editorItems.indexOf(item), 1)">移除</el-button>
        </div>
      </div>
      <p class="draft-total">当前预计花费 <strong>{{ formatMoney(previewPlanned) }}</strong></p>
    </section>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button v-if="mode === 'ai' && draft" :loading="generating" @click="generate">重新生成</el-button>
      <el-button v-if="mode === 'manual' || draft" type="primary" :loading="saving" @click="save">确认并保存行程</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.trip-create-form { margin-top: 24px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; }
.full-width { width: 100%; }
.generate-panel { padding: 30px 0 10px; text-align: center; }
.generate-panel p { margin-bottom: 18px; color: var(--ink-muted); font-size: 13px; }
.draft-preview { max-height: 52vh; overflow-y: auto; padding-right: 5px; }
.draft-title { margin: 18px 0; font-family: var(--font-display); font-size: 20px; }
.draft-day h3 { margin: 20px 0 10px; font-family: var(--font-display); font-size: 17px; }
.draft-item { display: grid; grid-template-columns: 90px 120px 1fr 110px; gap: 8px; margin-bottom: 10px; }
.draft-note { grid-column: 3 / 5; }
.draft-item > .el-button { grid-column: 1 / 3; grid-row: 2; justify-self: start; }
.draft-total { text-align: right; color: var(--ink-muted); }
.draft-total strong { color: var(--ink); font-size: 20px; }
@media (max-width: 640px) {
  .form-grid { grid-template-columns: 1fr; }
  .draft-item { grid-template-columns: 90px 1fr; padding-bottom: 12px; border-bottom: 1px solid var(--line-soft); }
  .draft-item > .el-input:nth-of-type(2), .draft-note { grid-column: 1 / -1; }
  .draft-item > .el-button { grid-column: 1 / -1; grid-row: auto; }
}
</style>
