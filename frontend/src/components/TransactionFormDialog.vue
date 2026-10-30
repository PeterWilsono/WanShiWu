<script setup lang="ts">
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { computed, reactive, ref, watch } from 'vue'

import { createTransaction, updateTransaction } from '../api/transactions'
import { ApiError } from '../api/http'
import type { Category, TransactionType } from '../types/category'
import type { Transaction } from '../types/transaction'
import { centsToYuanInput, yuanToCents } from '../utils/money'

interface FormState {
  amount: string
  type: TransactionType
  categoryId: number | null
  occurredAt: Date | null
  note: string
}

const props = defineProps<{
  modelValue: boolean
  transaction: Transaction | null
  categories: Category[]
}>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [transaction: Transaction, mode: 'create' | 'edit']
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const formError = ref('')
const form = reactive<FormState>(emptyForm())
const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})
const mode = computed(() => (props.transaction ? 'edit' : 'create'))
const availableCategories = computed(() =>
  props.categories.filter((category) => category.type === form.type),
)
const rules: FormRules<FormState> = {
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  categoryId: [{ required: true, message: '请选择分类', trigger: 'change' }],
  occurredAt: [{ required: true, message: '请选择发生时间', trigger: 'change' }],
}

function emptyForm(): FormState {
  return { amount: '', type: 'expense', categoryId: null, occurredAt: new Date(), note: '' }
}

function resetForm(): void {
  const item = props.transaction
  Object.assign(
    form,
    item
      ? {
          amount: centsToYuanInput(item.amount_cents),
          type: item.type,
          categoryId: item.category_id,
          occurredAt: new Date(item.occurred_at),
          note: item.note || '',
        }
      : emptyForm(),
  )
  if (!item) form.categoryId = availableCategories.value[0]?.id || null
  formError.value = ''
  formRef.value?.clearValidate()
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) resetForm()
  },
)
watch(
  () => form.type,
  () => {
    if (!availableCategories.value.some((category) => category.id === form.categoryId)) {
      form.categoryId = availableCategories.value[0]?.id || null
    }
  },
)

async function submit(): Promise<void> {
  formError.value = ''
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  const amountCents = yuanToCents(form.amount)
  if (amountCents === null) {
    formError.value = '金额必须为大于 0 的数字，最多两位小数'
    return
  }
  if (!form.categoryId || !form.occurredAt) return

  submitting.value = true
  try {
    const payload = {
      amount_cents: amountCents,
      type: form.type,
      category_id: form.categoryId,
      note: form.note.trim() || null,
      occurred_at: form.occurredAt.toISOString(),
    }
    const saved = props.transaction
      ? await updateTransaction(props.transaction.id, payload)
      : await createTransaction({ ...payload, source: 'manual' })
    emit('saved', saved, mode.value)
    visible.value = false
    ElMessage.success(mode.value === 'create' ? '账目已记录' : '账目已更新')
  } catch (error) {
    formError.value = error instanceof ApiError ? error.message : '保存失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="mode === 'create' ? '记一笔' : '编辑账目'"
    width="min(560px, 92vw)"
    :close-on-click-modal="false"
  >
    <el-alert v-if="formError" :title="formError" type="error" show-icon :closable="false" />
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="form">
      <el-form-item label="收支类型" prop="type">
        <el-radio-group v-model="form.type">
          <el-radio-button value="expense">支出</el-radio-button>
          <el-radio-button value="income">收入</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="金额（元）" prop="amount" required>
          <el-input v-model="form.amount" inputmode="decimal" placeholder="例如 19.90">
            <template #prefix>¥</template>
          </el-input>
        </el-form-item>
        <el-form-item label="分类" prop="categoryId" required>
          <el-select v-model="form.categoryId" class="full-width" placeholder="选择分类">
            <el-option
              v-for="category in availableCategories"
              :key="category.id"
              :label="category.name"
              :value="category.id"
            />
          </el-select>
        </el-form-item>
      </div>
      <p v-if="!availableCategories.length" class="form-hint">当前类型暂无分类，请先到分类管理添加。</p>
      <el-form-item label="发生时间" prop="occurredAt" required>
        <el-date-picker
          v-model="form.occurredAt"
          type="datetime"
          format="YYYY-MM-DD HH:mm"
          class="full-width"
          placeholder="实际收支时间"
        />
      </el-form-item>
      <el-form-item label="备注" prop="note">
        <el-input
          v-model="form.note"
          type="textarea"
          :rows="3"
          maxlength="200"
          show-word-limit
          placeholder="可选，最多 200 字"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.form {
  margin-top: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.full-width {
  width: 100%;
}

.form-hint {
  margin: -8px 0 16px;
  color: #e6a23c;
  font-size: 13px;
}

@media (max-width: 560px) {
  .form-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
}
</style>
