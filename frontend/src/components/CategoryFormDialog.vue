<script setup lang="ts">
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { computed, reactive, ref, watch } from 'vue'

import { createCategory, updateCategory } from '../api/categories'
import { ApiError } from '../api/http'
import type { Category, TransactionType } from '../types/category'

interface FormState {
  name: string
  type: TransactionType
  icon: string
}

const props = defineProps<{
  modelValue: boolean
  category: Category | null
  defaultType: TransactionType
}>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [category: Category]
}>()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const formError = ref('')
const form = reactive<FormState>({ name: '', type: 'expense', icon: '' })
const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})
const mode = computed(() => (props.category ? 'edit' : 'create'))
const rules: FormRules<FormState> = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { max: 30, message: '名称不能超过 30 个字符', trigger: 'blur' },
  ],
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    Object.assign(form, {
      name: props.category?.name || '',
      type: props.category?.type || props.defaultType,
      icon: props.category?.icon || '',
    })
    formError.value = ''
    formRef.value?.clearValidate()
  },
)

async function submit(): Promise<void> {
  formError.value = ''
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  if (!form.name.trim()) {
    formError.value = '分类名称不能只包含空白字符'
    return
  }

  submitting.value = true
  try {
    const saved = props.category
      ? await updateCategory(props.category.id, {
          name: form.name.trim(),
          icon: form.icon.trim() || null,
        })
      : await createCategory({
          name: form.name.trim(),
          type: form.type,
          icon: form.icon.trim() || null,
        })
    emit('saved', saved)
    visible.value = false
    ElMessage.success(mode.value === 'create' ? '分类已创建' : '分类已更新')
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
    :title="mode === 'create' ? '新建分类' : '编辑分类'"
    width="min(480px, 92vw)"
    :close-on-click-modal="false"
  >
    <el-alert v-if="formError" :title="formError" type="error" show-icon :closable="false" />
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="form">
      <el-form-item label="收支类型" prop="type">
        <el-radio-group v-model="form.type" :disabled="mode === 'edit'">
          <el-radio-button value="expense">支出</el-radio-button>
          <el-radio-button value="income">收入</el-radio-button>
        </el-radio-group>
        <p v-if="mode === 'edit'" class="form-hint">分类创建后不能改变收支类型。</p>
      </el-form-item>
      <el-form-item label="分类名称" prop="name" required>
        <el-input v-model="form.name" maxlength="30" placeholder="例如：交通、奖金" autofocus />
      </el-form-item>
      <el-form-item label="图标" prop="icon">
        <el-input v-model="form.icon" maxlength="30" placeholder="图标名称或符号（可选）" />
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
.form-hint {
  margin: 6px 0 0;
  color: #909399;
  font-size: 12px;
}
</style>
