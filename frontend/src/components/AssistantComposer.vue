<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import { cancelAssistantRecord, confirmAssistant, parseAssistant } from '../api/assistant'
import { ApiError } from '../api/http'
import type { ActionResult, AssistantAction, AssistantTool } from '../types/assistant'
import type { IngredientUnit, Storage } from '../types/pantry'
import { yuanToCents } from '../utils/money'

const router = useRouter()
const text = ref('')
const parsing = ref(false)
const confirming = ref(false)
const cancelling = ref(false)
const errorMessage = ref('')
const clarification = ref('')
const recordId = ref<number | null>(null)
const drafts = ref<ActionDraft[]>([])
const results = ref<ActionResult[]>([])

const supportedTools: AssistantTool[] = [
  'create_todo', 'create_event', 'add_expense', 'add_income', 'add_ingredient', 'save_bookmark', 'create_trip',
]

interface ActionDraft {
  tool: AssistantTool
  summary: string
  originalArgs: Record<string, unknown>
  title: string
  note: string
  dueAt: Date | null
  priority: number
  startAt: Date | null
  endAt: Date | null
  location: string
  remindBeforeMin: number | null
  amount: string
  category: string
  occurredAt: Date | null
  name: string
  quantity: string
  unit: IngredientUnit
  expireOn: string
  storage: Storage
  url: string
  destination: string
  days: number
  budget: string
  preferences: string
}

function optionalDate(value: unknown): Date | null {
  return typeof value === 'string' && value ? new Date(value) : null
}

function toDraft(action: AssistantAction): ActionDraft {
  const args = action.args
  return {
    tool: action.tool,
    summary: action.summary,
    originalArgs: { ...args },
    title: String(args.title ?? ''),
    note: String(args.note ?? ''),
    dueAt: optionalDate(args.due_at),
    priority: typeof args.priority === 'number' ? args.priority : 2,
    startAt: optionalDate(args.start_at),
    endAt: optionalDate(args.end_at),
    location: String(args.location ?? ''),
    remindBeforeMin: typeof args.remind_before_min === 'number' ? args.remind_before_min : null,
    amount: args.amount === undefined ? '' : String(args.amount),
    category: String(args.category ?? ''),
    occurredAt: optionalDate(args.occurred_at),
    name: String(args.name ?? ''),
    quantity: args.quantity === undefined ? '' : String(args.quantity),
    unit: String(args.unit ?? '个') as IngredientUnit,
    expireOn: String(args.expire_on ?? ''),
    storage: String(args.storage ?? 'room') as Storage,
    url: String(args.url ?? ''),
    destination: String(args.destination ?? ''),
    days: typeof args.days === 'number' ? args.days : 1,
    budget: args.budget === undefined || args.budget === null ? '' : String(args.budget),
    preferences: String(args.preferences ?? ''),
  }
}

const hasUnsupported = computed(() => drafts.value.some((item) => !supportedTools.includes(item.tool)))

function resetResult(): void {
  errorMessage.value = ''
  clarification.value = ''
  recordId.value = null
  drafts.value = []
  results.value = []
}

async function handleParse(): Promise<void> {
  const input = text.value.trim()
  if (!input) {
    errorMessage.value = '请先输入想记录的事情'
    return
  }
  parsing.value = true
  resetResult()
  try {
    const response = await parseAssistant(input)
    recordId.value = response.record_id
    clarification.value = response.clarification || ''
    drafts.value = response.actions.map(toDraft)
  } catch (error) {
    errorMessage.value = assistantError(error)
  } finally {
    parsing.value = false
  }
}

function assistantError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 42901) return '今日 AI 次数已用完，可明日再试或前往手动录入。'
    if (error.code === 50201) return 'AI 服务暂时不可用，请稍后重试或使用下方手动功能。'
    if (error.code === 50202) return 'AI 没有理解这句话，请补充时间、金额等信息或手动填写。'
    return error.message
  }
  return '操作失败，请稍后重试'
}

function toAction(draft: ActionDraft): AssistantAction {
  const args = { ...draft.originalArgs }
  if (draft.tool === 'create_todo') {
    Object.assign(args, {
      title: draft.title.trim(),
      note: draft.note.trim() || null,
      due_at: draft.dueAt?.toISOString() || null,
      priority: draft.priority,
    })
  } else if (draft.tool === 'create_event') {
    Object.assign(args, {
      title: draft.title.trim(),
      start_at: draft.startAt?.toISOString(),
      end_at: draft.endAt?.toISOString() || null,
      location: draft.location.trim() || null,
      remind_before_min: draft.remindBeforeMin,
    })
  } else if (draft.tool === 'add_ingredient') {
    const quantity = draft.quantity.trim()
    if (!/^\d{1,8}(?:\.\d{1,2})?$/.test(quantity) || Number(quantity) <= 0) {
      throw new Error('食材数量必须大于 0，且最多保留两位小数')
    }
    Object.assign(args, {
      name: draft.name.trim(),
      quantity,
      unit: draft.unit,
      expire_on: draft.expireOn || null,
      storage: draft.storage,
    })
  } else if (draft.tool === 'save_bookmark') {
    Object.assign(args, { url: draft.url.trim(), note: draft.note.trim() || null })
  } else if (draft.tool === 'create_trip') {
    const budget = draft.budget.trim()
    if (budget && !/^(0|[1-9]\d*)(?:\.\d{1,2})?$/.test(budget)) {
      throw new Error('旅行预算需为非负数字，最多两位小数')
    }
    const cents = budget ? Math.round(Number(budget) * 100) : null
    if (cents !== null && (!Number.isSafeInteger(cents) || cents > 9_999_999_999)) {
      throw new Error('旅行预算超出可支持的范围')
    }
    Object.assign(args, {
      destination: draft.destination.trim(),
      days: draft.days,
      budget: cents === null ? null : cents / 100,
      preferences: draft.preferences.trim() || null,
    })
  } else if (draft.tool === 'add_expense' || draft.tool === 'add_income') {
    const cents = yuanToCents(draft.amount)
    if (cents === null) throw new Error('金额必须是大于 0 且最多两位小数的数字')
    Object.assign(args, {
      amount: cents / 100,
      category: draft.category.trim(),
      note: draft.note.trim() || null,
      occurred_at: draft.occurredAt?.toISOString() || null,
    })
  }
  return { tool: draft.tool, args, summary: draft.summary }
}

function validateDrafts(actions: AssistantAction[]): void {
  for (const action of actions) {
    if (action.tool === 'create_todo' && !action.args.title) throw new Error('待办标题不能为空')
    if (action.tool === 'create_event') {
      if (!action.args.title || !action.args.start_at) throw new Error('日程标题和开始时间不能为空')
      if (action.args.end_at && String(action.args.end_at) < String(action.args.start_at)) {
        throw new Error('日程结束时间不能早于开始时间')
      }
    }
    if ((action.tool === 'add_expense' || action.tool === 'add_income') && !action.args.category) {
      throw new Error('请选择或填写收支分类')
    }
    if (action.tool === 'add_ingredient' && !action.args.name) {
      throw new Error('食材名称不能为空')
    }
    if (action.tool === 'save_bookmark' && !/^https?:\/\//.test(String(action.args.url))) {
      throw new Error('收藏链接必须以 http:// 或 https:// 开头')
    }
    if (action.tool === 'create_trip' && !action.args.destination) {
      throw new Error('旅行目的地不能为空')
    }
  }
}

async function handleConfirm(): Promise<void> {
  if (recordId.value === null || hasUnsupported.value) return
  confirming.value = true
  errorMessage.value = ''
  try {
    const actions = drafts.value.map(toAction)
    validateDrafts(actions)
    const response = await confirmAssistant({ record_id: recordId.value, actions })
    results.value = response.results
    drafts.value = []
    text.value = ''
    ElMessage.success('已确认并写入')
  } catch (error) {
    errorMessage.value = error instanceof Error && !(error instanceof ApiError)
      ? error.message
      : assistantError(error)
  } finally {
    confirming.value = false
  }
}

async function handleCancel(): Promise<void> {
  if (recordId.value === null) return
  cancelling.value = true
  errorMessage.value = ''
  try {
    await cancelAssistantRecord(recordId.value)
    resetResult()
    ElMessage.success('已取消，未写入任何数据')
  } catch (error) {
    errorMessage.value = assistantError(error)
  } finally {
    cancelling.value = false
  }
}

function resultRoute(result: ActionResult): string {
  if (result.ref.startsWith('todo:')) return '/todos'
  if (result.ref.startsWith('event:')) return '/events'
  if (result.ref.startsWith('ingredient:')) return '/pantry'
  if (result.ref.startsWith('bookmark:')) return '/inbox'
  if (result.ref.startsWith('trip:')) return `/trip/${result.id}`
  return '/transactions'
}

function goToResult(result: ActionResult): void {
  void router.push(resultRoute(result))
}

function toolName(tool: AssistantTool): string {
  return {
    create_todo: '新建待办',
    create_event: '新建日程',
    add_expense: '记一笔支出',
    add_income: '记一笔收入',
    add_ingredient: '添加食材',
    save_bookmark: '收藏链接',
    create_trip: '创建旅行',
    ask_clarification: '补充信息',
  }[tool]
}
</script>

<template>
  <section class="assistant" aria-label="AI 全局输入">
    <div class="assistant__heading">
      <h2>对万事屋说点什么</h2>
      <span>AI 只生成候选动作，确认后才会写入</span>
    </div>
    <el-input
      v-model="text"
      type="textarea"
      :rows="2"
      maxlength="2000"
      placeholder="例如：明天下午三点约了牙医；买了 6 个鸡蛋放冷藏"
      @keydown.ctrl.enter="handleParse"
    />
    <div class="assistant__parse-row">
      <span>Ctrl + Enter 快速解析</span>
      <el-button type="primary" :loading="parsing" :disabled="!text.trim()" @click="handleParse">
        {{ parsing ? '正在理解…' : '解析' }}
      </el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      show-icon
      class="assistant__message"
    />
    <el-alert
      v-if="clarification"
      :title="clarification"
      description="请补充信息后重新解析，系统不会猜测缺失内容。"
      type="warning"
      :closable="false"
      show-icon
      class="assistant__message"
    />

    <div v-if="drafts.length" class="assistant__drafts">
      <el-card v-for="(draft, index) in drafts" :key="index" shadow="never" class="draft-card">
        <template #header>
          <div class="draft-card__header">
            <strong>{{ toolName(draft.tool) }}</strong>
            <span>第 {{ index + 1 }} 个动作</span>
          </div>
        </template>

        <el-alert
          v-if="!supportedTools.includes(draft.tool)"
          :title="`${draft.summary}：对应模块尚未开放，暂时不能确认。`"
          type="info"
          :closable="false"
        />
        <el-form v-else label-position="top" class="draft-form">
          <template v-if="draft.tool === 'create_todo'">
            <el-form-item label="标题" required><el-input v-model="draft.title" maxlength="200" /></el-form-item>
            <div class="draft-form__grid">
              <el-form-item label="截止时间"><el-date-picker v-model="draft.dueAt" type="datetime" class="full-width" /></el-form-item>
              <el-form-item label="优先级"><el-input-number v-model="draft.priority" :min="1" :max="3" class="full-width" /></el-form-item>
            </div>
            <el-form-item label="备注"><el-input v-model="draft.note" type="textarea" :rows="2" /></el-form-item>
          </template>
          <template v-else-if="draft.tool === 'create_event'">
            <el-form-item label="标题" required><el-input v-model="draft.title" maxlength="200" /></el-form-item>
            <div class="draft-form__grid">
              <el-form-item label="开始时间" required><el-date-picker v-model="draft.startAt" type="datetime" class="full-width" /></el-form-item>
              <el-form-item label="结束时间"><el-date-picker v-model="draft.endAt" type="datetime" class="full-width" /></el-form-item>
              <el-form-item label="地点"><el-input v-model="draft.location" maxlength="200" /></el-form-item>
              <el-form-item label="提前提醒（分钟）"><el-input-number v-model="draft.remindBeforeMin" :min="0" class="full-width" /></el-form-item>
            </div>
          </template>
          <template v-else-if="draft.tool === 'add_expense' || draft.tool === 'add_income'">
            <div class="draft-form__grid">
              <el-form-item label="金额（元）" required><el-input v-model="draft.amount" placeholder="例如 35.50" /></el-form-item>
              <el-form-item label="分类" required><el-input v-model="draft.category" maxlength="30" placeholder="例如 餐饮" /></el-form-item>
            </div>
            <el-form-item label="发生时间"><el-date-picker v-model="draft.occurredAt" type="datetime" class="full-width" /></el-form-item>
            <el-form-item label="备注"><el-input v-model="draft.note" maxlength="200" /></el-form-item>
          </template>
          <template v-else-if="draft.tool === 'save_bookmark'">
            <el-form-item label="链接" required><el-input v-model="draft.url" placeholder="https://example.com/article" /></el-form-item>
            <el-form-item label="备注"><el-input v-model="draft.note" type="textarea" :rows="2" maxlength="500" /></el-form-item>
          </template>
          <template v-if="draft.tool === 'create_trip'">
            <div class="draft-form__grid">
              <el-form-item label="目的地" required><el-input v-model="draft.destination" maxlength="100" /></el-form-item>
              <el-form-item label="天数" required><el-input-number v-model="draft.days" :min="1" :max="30" class="full-width" /></el-form-item>
            </div>
            <el-form-item label="总预算（元，可留空或为 0）"><el-input v-model="draft.budget" placeholder="例如 3000.00" /></el-form-item>
            <el-form-item label="旅行偏好"><el-input v-model="draft.preferences" type="textarea" :rows="2" maxlength="1000" /></el-form-item>
            <el-alert title="这里只创建空白行程草稿，详细每日安排可在旅行页面使用 AI 生成。" type="info" :closable="false" />
          </template>
          <template v-if="draft.tool === 'add_ingredient'">
            <el-form-item label="食材名称" required><el-input v-model="draft.name" maxlength="50" /></el-form-item>
            <div class="draft-form__grid">
              <el-form-item label="数量" required><el-input v-model="draft.quantity" placeholder="例如 6 或 2.50" /></el-form-item>
              <el-form-item label="单位" required>
                <el-select v-model="draft.unit" class="full-width">
                  <el-option v-for="unit in ['个', '克', '千克', '毫升', '升', '包', '瓶']" :key="unit" :label="unit" :value="unit" />
                </el-select>
              </el-form-item>
              <el-form-item label="保质期">
                <el-date-picker v-model="draft.expireOn" type="date" value-format="YYYY-MM-DD" class="full-width" />
              </el-form-item>
              <el-form-item label="存放方式">
                <el-select v-model="draft.storage" class="full-width">
                  <el-option label="冷藏" value="fridge" /><el-option label="冷冻" value="freezer" /><el-option label="常温" value="room" />
                </el-select>
              </el-form-item>
            </div>
          </template>
        </el-form>
      </el-card>
      <div class="assistant__confirm-row">
        <el-button :loading="cancelling" :disabled="confirming" @click="handleCancel">取消记录</el-button>
        <el-button type="primary" :loading="confirming" :disabled="hasUnsupported || cancelling" @click="handleConfirm">
          确认并写入 {{ drafts.length }} 个动作
        </el-button>
      </div>
    </div>

    <el-result v-if="results.length" icon="success" title="写入成功" sub-title="数据已由业务代码保存，可前往对应模块查看。">
      <template #extra>
        <el-button v-for="result in results" :key="result.ref" type="primary" plain @click="goToResult(result)">
          查看{{ toolName(result.tool).replace('新建', '').replace('记一笔', '').replace('添加', '') }}
        </el-button>
        <el-button @click="results = []">继续输入</el-button>
      </template>
    </el-result>
  </section>
</template>

<style scoped>
.assistant { width: 100%; text-align: left; }
.assistant__heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 18px; }
.assistant__heading h2 { font-family: var(--font-display); font-size: 22px; font-weight: 600; letter-spacing: .02em; }
.assistant__heading span, .assistant__parse-row span { color: var(--ink-muted); font-size: 10px; line-height: 1.6; }
.assistant :deep(.el-textarea__inner) { min-height: 100px !important; border: 0; background: var(--paper); font-size: 14px; resize: vertical; }
.assistant__parse-row, .assistant__confirm-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 16px; }
.assistant__parse-row .el-button { min-width: 96px; }
.assistant__message { margin-top: 16px; }
.assistant__drafts { margin-top: 22px; }
.draft-card { background: var(--paper); box-shadow: none; }
.draft-card + .draft-card { margin-top: 12px; }
.draft-card__header { display: flex; justify-content: space-between; }
.draft-card__header strong { font-family: var(--font-display); font-size: 17px; }
.draft-card__header span { color: var(--ink-muted); font-size: 12px; }
.draft-form__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.full-width { width: 100%; }
.assistant__confirm-row { justify-content: flex-end; }
@media (max-width: 640px) {
  .assistant__heading { align-items: flex-start; flex-direction: column; gap: 5px; }
  .assistant__parse-row > span { display: none; }
  .assistant__parse-row { justify-content: flex-end; }
  .draft-form__grid { grid-template-columns: 1fr; gap: 0; }
  .assistant__confirm-row { align-items: stretch; flex-direction: column-reverse; }
}
</style>
