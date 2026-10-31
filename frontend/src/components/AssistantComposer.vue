<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import { cancelAssistantRecord, confirmAssistant, parseAssistant } from '../api/assistant'
import { ApiError } from '../api/http'
import type { ActionResult, AssistantAction, AssistantTool } from '../types/assistant'
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

const supportedTools: AssistantTool[] = ['create_todo', 'create_event', 'add_expense', 'add_income']

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
  return '/transactions'
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
      placeholder="例如：明天下午三点约了牙医；午饭花了35"
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
          <template v-else>
            <div class="draft-form__grid">
              <el-form-item label="金额（元）" required><el-input v-model="draft.amount" placeholder="例如 35.50" /></el-form-item>
              <el-form-item label="分类" required><el-input v-model="draft.category" maxlength="30" placeholder="例如 餐饮" /></el-form-item>
            </div>
            <el-form-item label="发生时间"><el-date-picker v-model="draft.occurredAt" type="datetime" class="full-width" /></el-form-item>
            <el-form-item label="备注"><el-input v-model="draft.note" maxlength="200" /></el-form-item>
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
        <el-button v-for="result in results" :key="result.ref" type="primary" plain @click="router.push(resultRoute(result))">
          查看{{ toolName(result.tool).replace('新建', '').replace('记一笔', '') }}
        </el-button>
        <el-button @click="results = []">继续输入</el-button>
      </template>
    </el-result>
  </section>
</template>

<style scoped>
.assistant { width: 100%; text-align: left; }
.assistant__heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.assistant__heading h2 { margin: 0; font-size: 20px; }
.assistant__heading span, .assistant__parse-row span { color: #909399; font-size: 13px; }
.assistant__parse-row, .assistant__confirm-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 12px; }
.assistant__message { margin-top: 16px; }
.assistant__drafts { margin-top: 18px; }
.draft-card + .draft-card { margin-top: 12px; }
.draft-card__header { display: flex; justify-content: space-between; }
.draft-card__header span { color: #909399; font-size: 13px; }
.draft-form__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.full-width { width: 100%; }
.assistant__confirm-row { justify-content: flex-end; }
@media (max-width: 640px) {
  .assistant__heading { align-items: flex-start; flex-direction: column; }
  .draft-form__grid { grid-template-columns: 1fr; gap: 0; }
}
</style>
