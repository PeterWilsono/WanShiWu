<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, onUnmounted, ref } from 'vue'

import {
  deleteBookmark, listBookmarks, listTags, retryBookmark, searchBookmarks, updateBookmarkContent,
} from '../api/inbox'
import { ApiError } from '../api/http'
import BookmarkCard from '../components/BookmarkCard.vue'
import BookmarkFormDialog from '../components/BookmarkFormDialog.vue'
import WeeklyDigestPanel from '../components/WeeklyDigestPanel.vue'
import type { Bookmark, BookmarkStatus, Tag } from '../types/inbox'

const activeTab = ref('bookmarks')
const items = ref<Bookmark[]>([])
const tags = ref<Tag[]>([])
const loading = ref(false)
const loadError = ref('')
const query = ref('')
const appliedQuery = ref('')
const status = ref<BookmarkStatus | ''>('')
const selectedTag = ref('')
const page = ref(1)
const total = ref(0)
const pageSize = 9
const dialogVisible = ref(false)
const editing = ref<Bookmark | null>(null)
const contentVisible = ref(false)
const contentTarget = ref<Bookmark | null>(null)
const contentText = ref('')
const actionId = ref<number | null>(null)
const contentSubmitting = ref(false)

function message(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

async function load(showLoading = true): Promise<void> {
  if (showLoading) loading.value = true
  loadError.value = ''
  try {
    const result = appliedQuery.value
      ? await searchBookmarks(appliedQuery.value, page.value, pageSize)
      : await listBookmarks({
          page: page.value, page_size: pageSize,
          status: status.value || undefined, tag: selectedTag.value || undefined,
        })
    items.value = result.items
    total.value = result.total
  } catch (error) {
    loadError.value = message(error, '收藏加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function loadTags(): Promise<void> {
  try { tags.value = await listTags() } catch { tags.value = [] }
}
function applyFilters(): void { page.value = 1; void load() }
function clearFilters(): void {
  query.value = ''; appliedQuery.value = ''; status.value = ''; selectedTag.value = ''; applyFilters()
}
function openCreate(): void { editing.value = null; dialogVisible.value = true }
function openEdit(item: Bookmark): void { editing.value = item; dialogVisible.value = true }
async function saved(): Promise<void> { await Promise.all([load(), loadTags()]) }

async function remove(item: Bookmark): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除“${item.title || item.url}”吗？`, '删除收藏', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch { return }
  actionId.value = item.id
  try {
    await deleteBookmark(item.id); ElMessage.success('收藏已删除')
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await load()
  } catch (error) { ElMessage.error(message(error, '删除失败')) } finally { actionId.value = null }
}
async function retry(item: Bookmark): Promise<void> {
  actionId.value = item.id
  try { await retryBookmark(item.id); ElMessage.success('已重新加入整理队列'); await load() }
  catch (error) { ElMessage.error(message(error, '重试失败')) } finally { actionId.value = null }
}
function openContent(item: Bookmark): void {
  contentTarget.value = item; contentText.value = item.content ?? ''; contentVisible.value = true
}
async function saveContent(generateSummary = true): Promise<void> {
  if (!contentTarget.value || !contentText.value.trim()) { ElMessage.warning('请先粘贴正文'); return }
  contentSubmitting.value = true
  try {
    await updateBookmarkContent(contentTarget.value.id, contentText.value.trim(), generateSummary)
    ElMessage.success(generateSummary ? '正文与摘要已更新' : '正文已保存，可稍后生成摘要')
    contentVisible.value = false
    await Promise.all([load(), loadTags()])
  } catch (error) { ElMessage.error(message(error, '摘要生成失败，正文已保留，可稍后重试')) }
  finally { contentSubmitting.value = false }
}

const timer = window.setInterval(() => {
  if (activeTab.value === 'bookmarks' && items.value.some((item) => ['pending', 'processing'].includes(item.status))) {
    void load(false)
  }
}, 15_000)
onMounted(() => { void load(); void loadTags() })
onUnmounted(() => window.clearInterval(timer))
</script>

<template>
  <main class="inbox-page">
    <header class="inbox-hero">
      <div><p>READING ARCHIVE · 收藏箱</p><h1>阅读，不必赶在此刻。</h1><span>把值得回看的内容收好，让链接慢慢长成自己的知识手帖。</span></div>
      <el-button type="primary" @click="openCreate">收藏链接</el-button>
    </header>
    <el-tabs v-model="activeTab" class="inbox-tabs">
      <el-tab-pane label="我的收藏" name="bookmarks">
        <section class="inbox-toolbar" aria-label="收藏筛选">
          <el-input v-model="query" clearable placeholder="搜索标题、摘要或正文" @keyup.enter="appliedQuery = query.trim(); applyFilters()" />
          <el-select v-model="status" clearable placeholder="全部状态" @change="applyFilters">
            <el-option label="等待整理" value="pending" /><el-option label="正在整理" value="processing" />
            <el-option label="已归档" value="success" /><el-option label="需要处理" value="failed" />
          </el-select>
          <el-select v-model="selectedTag" clearable filterable placeholder="全部标签" @change="applyFilters">
            <el-option v-for="tag in tags" :key="tag.id" :label="tag.name" :value="tag.name" />
          </el-select>
          <el-button type="primary" plain @click="appliedQuery = query.trim(); applyFilters()">查找</el-button>
          <el-button text @click="clearFilters">清空</el-button>
        </section>
        <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false"><el-button size="small" @click="load()">重试</el-button></el-alert>
        <section v-loading="loading" class="bookmark-section" aria-live="polite">
          <el-empty v-if="!loading && !items.length && !loadError" description="这里还很安静，先收藏一篇真正想读的内容吧。">
            <el-button type="primary" @click="openCreate">收藏第一篇</el-button>
          </el-empty>
          <div v-else class="bookmark-grid">
            <BookmarkCard v-for="item in items" :key="item.id" :bookmark="item" :busy="actionId === item.id"
              @edit="openEdit(item)" @remove="remove(item)" @retry="retry(item)" @content="openContent(item)" />
          </div>
        </section>
        <el-pagination v-if="total > pageSize" v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="load()" />
      </el-tab-pane>
      <el-tab-pane label="每周回顾" name="weekly"><WeeklyDigestPanel /></el-tab-pane>
    </el-tabs>
    <BookmarkFormDialog v-model="dialogVisible" :bookmark="editing" @saved="saved" />
    <el-dialog v-model="contentVisible" title="收藏正文" width="min(720px, 94vw)">
      <div class="content-guide">
        <p>AI 不会自行打开链接；系统会先在服务器读取公开网页。遇到登录、验证码或动态页面时，可以打开原文复制正文。</p>
        <a v-if="contentTarget" :href="contentTarget.url" target="_blank" rel="noopener noreferrer">打开原文并复制正文</a>
      </div>
      <el-input v-model="contentText" type="textarea" :rows="14" maxlength="100000" placeholder="粘贴文章正文……" />
      <template #footer>
        <el-button @click="contentVisible = false">关闭</el-button>
        <el-button :disabled="contentSubmitting" @click="saveContent(false)">仅保存正文</el-button>
        <el-button type="primary" :loading="contentSubmitting" @click="saveContent()">保存并生成摘要</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<style scoped>
.inbox-page { width: min(1280px, 100%); margin: 0 auto; padding: 58px 36px 80px; }
.inbox-hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 28px; margin-bottom: 38px; }
.inbox-hero p { color: var(--vermilion); font-size: 10px; font-weight: 700; letter-spacing: .2em; }
.inbox-hero h1 { margin: 14px 0; font-family: var(--font-display); font-size: clamp(36px, 4vw, 52px); font-weight: 500; letter-spacing: -.04em; }
.inbox-hero span { color: var(--ink-muted); font-size: 13px; line-height: 1.8; }
.inbox-tabs :deep(.el-tabs__nav-wrap::after) { background: var(--line-soft); }
.inbox-toolbar { display: grid; grid-template-columns: minmax(220px, 1fr) 150px 150px auto auto; gap: 10px; margin: 24px 0; }
.bookmark-section { min-height: 280px; }
.bookmark-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.el-pagination { justify-content: center; margin-top: 30px; }
.content-guide { margin-bottom: 16px; padding: 12px 14px; border-radius: 3px 10px 3px 3px; background: var(--paper-deep); }
.content-guide p { margin: 0 0 7px; color: var(--ink-secondary); font-size: 12px; line-height: 1.8; }
.content-guide a { color: var(--vermilion); font-size: 12px; text-decoration: none; }
@media (max-width: 1050px) { .bookmark-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .inbox-toolbar { grid-template-columns: 1fr 1fr 1fr; } .inbox-toolbar .el-input { grid-column: 1 / -1; } }
@media (max-width: 640px) { .inbox-page { padding: 38px 18px 60px; } .inbox-hero { align-items: flex-start; flex-direction: column; } .inbox-hero h1 { font-size: 38px; } .inbox-toolbar { grid-template-columns: 1fr 1fr; } .bookmark-grid { grid-template-columns: 1fr; } }
</style>
