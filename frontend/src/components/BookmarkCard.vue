<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import type { Bookmark, BookmarkStatus } from '../types/inbox'

defineProps<{ bookmark: Bookmark; busy: boolean }>()
const emit = defineEmits<{
  edit: []
  remove: []
  retry: []
  content: []
}>()

const statusLabels: Record<BookmarkStatus, string> = {
  pending: '等待整理', processing: '正在整理', success: '已归档', failed: '需要处理',
}
</script>

<template>
  <article class="bookmark-card" :class="`bookmark-card--${bookmark.status}`">
    <header>
      <span class="bookmark-card__status"><i />{{ statusLabels[bookmark.status] }}</span>
      <a :href="bookmark.url" target="_blank" rel="noopener noreferrer" :title="bookmark.url">
        {{ bookmark.source_domain || '查看原文' }}<AppIcon name="arrow" :size="14" />
      </a>
    </header>
    <h2>{{ bookmark.title || '尚未命名的收藏' }}</h2>
    <p v-if="bookmark.summary" class="bookmark-card__summary">{{ bookmark.summary }}</p>
    <p v-else-if="bookmark.status === 'failed'" class="bookmark-card__error">
      {{ bookmark.fail_reason || '整理失败，请重试或手动粘贴正文。' }}
    </p>
    <p v-else class="bookmark-card__pending">链接已收好，摘要与自动标签整理后会出现在这里。</p>
    <p v-if="bookmark.note" class="bookmark-card__note">“{{ bookmark.note }}”</p>
    <div v-if="bookmark.tags.length" class="bookmark-card__tags">
      <span v-for="tag in bookmark.tags" :key="tag.id" :class="{ ai: tag.source === 'ai' }">
        {{ tag.source === 'ai' ? 'AI · ' : '' }}{{ tag.name }}
      </span>
    </div>
    <footer>
      <div>
        <el-button text @click="emit('edit')">编辑</el-button>
        <el-button v-if="bookmark.status === 'failed'" text type="primary" :loading="busy" @click="emit('retry')">重试</el-button>
        <el-button text :disabled="busy" @click="emit('content')">{{ bookmark.content ? '查看 / 补正文' : '补正文' }}</el-button>
      </div>
      <el-button text type="danger" :disabled="busy" @click="emit('remove')">删除</el-button>
    </footer>
  </article>
</template>

<style scoped>
.bookmark-card { display: flex; min-width: 0; min-height: 320px; flex-direction: column; padding: 26px; border: 1px solid var(--line-soft); border-radius: 3px 22px 3px 3px; background: var(--paper-light); transition: transform .25s ease, box-shadow .25s ease; }
.bookmark-card:hover { box-shadow: var(--shadow-soft); transform: translateY(-3px); }
.bookmark-card > header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.bookmark-card__status { display: flex; align-items: center; gap: 7px; color: var(--ink-muted); font-size: 10px; letter-spacing: .08em; }
.bookmark-card__status i { width: 6px; height: 6px; border-radius: 50%; background: var(--sage); }
.bookmark-card--failed .bookmark-card__status i { background: var(--danger); }
.bookmark-card--pending .bookmark-card__status i, .bookmark-card--processing .bookmark-card__status i { background: var(--gold); }
.bookmark-card a { display: inline-flex; min-width: 0; align-items: center; gap: 5px; overflow: hidden; color: var(--vermilion); font-size: 10px; text-decoration: none; text-overflow: ellipsis; white-space: nowrap; }
h2 { margin: 24px 0 14px; overflow-wrap: anywhere; font-family: var(--font-display); font-size: 24px; font-weight: 600; line-height: 1.5; }
.bookmark-card__summary, .bookmark-card__pending, .bookmark-card__error { display: -webkit-box; overflow: hidden; color: var(--ink-secondary); font-size: 13px; line-height: 1.9; -webkit-box-orient: vertical; -webkit-line-clamp: 4; }
.bookmark-card__error { color: var(--danger); }
.bookmark-card__note { margin-top: 16px; color: var(--ink-muted); font-family: var(--font-display); font-size: 13px; line-height: 1.7; }
.bookmark-card__tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 18px; }
.bookmark-card__tags span { padding: 4px 9px; border-radius: 99px; color: var(--ink-secondary); background: var(--paper-deep); font-size: 10px; }
.bookmark-card__tags span.ai { color: var(--vermilion); background: rgb(196 91 63 / 10%); }
.bookmark-card footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: auto; padding-top: 20px; border-top: 1px solid var(--line-soft); }
.bookmark-card footer > div { display: flex; flex-wrap: wrap; }
.bookmark-card :deep(.el-button) { margin-left: 0; padding-right: 10px; padding-left: 0; }
@media (max-width: 520px) { .bookmark-card { min-height: 290px; padding: 22px; } }
</style>
