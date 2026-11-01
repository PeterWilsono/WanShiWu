<script setup lang="ts">
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { computed, ref, watch } from 'vue'

import { createBookmark, updateBookmark } from '../api/inbox'
import { ApiError } from '../api/http'
import type { Bookmark } from '../types/inbox'

const props = defineProps<{ modelValue: boolean; bookmark: Bookmark | null }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [bookmark: Bookmark]
}>()
const visible = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = ref({ url: '', title: '', note: '', tagsText: '' })
const rules: FormRules = {
  url: [{ required: true, message: '请输入要收藏的链接', trigger: 'blur' }],
}

watch(visible, (open) => {
  if (!open) return
  form.value.url = props.bookmark?.url ?? ''
  form.value.title = props.bookmark?.title ?? ''
  form.value.note = props.bookmark?.note ?? ''
  form.value.tagsText = props.bookmark?.tags
    .filter((tag) => tag.source === 'manual')
    .map((tag) => tag.name)
    .join('，') ?? ''
  formRef.value?.clearValidate()
})

function tags(): string[] {
  return [...new Set(form.value.tagsText.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean))]
}

async function submit(): Promise<void> {
  if (!formRef.value) return
  try { await formRef.value.validate() } catch { return }
  submitting.value = true
  try {
    const common = {
      title: form.value.title || null,
      note: form.value.note || null,
      tags: tags(),
    }
    const bookmark = props.bookmark
      ? await updateBookmark(props.bookmark.id, common)
      : await createBookmark({ url: form.value.url.trim(), ...common })
    ElMessage.success(props.bookmark ? '收藏已更新' : '已保存，正在后台整理')
    emit('saved', bookmark)
    visible.value = false
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '保存失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" :title="bookmark ? '编辑收藏' : '收藏一个链接'" width="min(560px, 92vw)">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
      <el-form-item label="链接" prop="url" required>
        <el-input v-model="form.url" :disabled="Boolean(bookmark)" placeholder="https://example.com/article" />
      </el-form-item>
      <el-form-item label="标题（可留空，抓取后自动补充）">
        <el-input v-model="form.title" maxlength="300" placeholder="这篇内容叫什么？" />
      </el-form-item>
      <el-form-item label="手动标签">
        <el-input v-model="form.tagsText" placeholder="用逗号分隔，例如：阅读，效率" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.note" type="textarea" :rows="3" maxlength="500" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">{{ bookmark ? '保存修改' : '保存并整理' }}</el-button>
    </template>
  </el-dialog>
</template>
