<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { listWeeklyDigests } from '../api/inbox'
import { ApiError } from '../api/http'
import type { WeeklyDigest } from '../types/inbox'

const items = ref<WeeklyDigest[]>([])
const loading = ref(false)
const errorMessage = ref('')

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    items.value = (await listWeeklyDigests()).items
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '周报加载失败'
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <section v-loading="loading" class="digest-panel">
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon>
      <el-button size="small" @click="load">重新加载</el-button>
    </el-alert>
    <el-empty v-else-if="!loading && !items.length" description="每周日 20:00，会把这一周的收藏整理成一封回顾。" />
    <article v-for="digest in items" v-else :key="digest.id" class="digest-card">
      <header><span>WEEKLY REVIEW</span><time>{{ digest.week_start }} 起 · {{ digest.bookmark_count }} 篇收藏</time></header>
      <div class="digest-card__content">{{ digest.content_md }}</div>
    </article>
  </section>
</template>

<style scoped>
.digest-panel { min-height: 260px; }
.digest-card { max-width: 820px; margin: 0 auto 20px; padding: 34px; border: 1px solid var(--line-soft); border-radius: 3px 24px 3px 3px; background: var(--paper-light); }
.digest-card header { display: flex; justify-content: space-between; gap: 20px; padding-bottom: 18px; border-bottom: 1px solid var(--line-soft); }
.digest-card header span { color: var(--vermilion); font-size: 10px; font-weight: 700; letter-spacing: .2em; }
.digest-card time { color: var(--ink-muted); font-size: 12px; }
.digest-card__content { padding-top: 24px; color: var(--ink-secondary); font-family: var(--font-display); font-size: 16px; line-height: 2; white-space: pre-wrap; }
@media (max-width: 520px) { .digest-card { padding: 24px 20px; } .digest-card header { flex-direction: column; gap: 8px; } }
</style>
