<script setup lang="ts">
import { ElMessage, ElNotification } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '../api/http'
import { listUnreadNotifications, markNotificationRead } from '../api/notifications'
import { useAuthStore } from '../stores/auth'
import type { AppNotification } from '../types/notification'
import { formatDateTime } from '../utils/time'

const POLL_INTERVAL_MS = 30_000
const authStore = useAuthStore()
const router = useRouter()
const notifications = ref<AppNotification[]>([])
const unreadCount = ref(0)
const loading = ref(false)
const loadError = ref('')
const actionId = ref<number | null>(null)
const popoverVisible = ref(false)
const initialized = ref(false)
const timeZone = computed(() => authStore.user?.timezone || 'Asia/Shanghai')
let timer: number | undefined

async function refresh(): Promise<void> {
  if (loading.value) return
  loading.value = true
  try {
    const result = await listUnreadNotifications()
    if (initialized.value) {
      const knownIds = new Set(notifications.value.map((item) => item.id))
      const latest = result.items.find((item) => !knownIds.has(item.id))
      if (latest) ElNotification({ title: '新提醒', message: latest.message, type: 'info' })
    }
    notifications.value = result.items
    unreadCount.value = result.unread_count
    loadError.value = ''
    initialized.value = true
  } catch (error) {
    // 后台轮询失败不反复弹全局消息；保留旧数据，并在通知面板中提供重试。
    loadError.value = error instanceof ApiError ? error.message : '通知加载失败'
  } finally {
    loading.value = false
  }
}

async function markRead(item: AppNotification): Promise<void> {
  actionId.value = item.id
  try {
    await markNotificationRead(item.id)
    notifications.value = notifications.value.filter((candidate) => candidate.id !== item.id)
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '操作失败，请稍后重试')
  } finally {
    actionId.value = null
  }
}

function openTarget(item: AppNotification): void {
  if (item.target_type === 'event') void router.push({ name: 'events' })
  if (item.target_type === 'todo') void router.push({ name: 'todos' })
  popoverVisible.value = false
}

function handleVisibility(): void {
  if (!document.hidden) void refresh()
}

onMounted(() => {
  void refresh()
  timer = window.setInterval(() => {
    if (!document.hidden) void refresh()
  }, POLL_INTERVAL_MS)
  document.addEventListener('visibilitychange', handleVisibility)
})

onBeforeUnmount(() => {
  if (timer !== undefined) window.clearInterval(timer)
  document.removeEventListener('visibilitychange', handleVisibility)
})
</script>

<template>
  <div class="notification-center">
    <el-popover
      v-model:visible="popoverVisible"
      placement="bottom-end"
      trigger="click"
      :width="390"
      @show="refresh"
    >
      <template #reference>
        <el-badge :value="unreadCount" :max="99" :hidden="unreadCount === 0">
          <el-button aria-label="未读通知">通知</el-button>
        </el-badge>
      </template>
      <section class="notification-panel" aria-live="polite">
        <header class="panel-header">
          <strong>未读提醒</strong>
          <el-button size="small" text :loading="loading" @click="refresh">刷新</el-button>
        </header>
        <el-alert
          v-if="loadError"
          :title="loadError"
          type="warning"
          show-icon
          :closable="false"
          class="load-alert"
        />
        <el-empty v-if="!notifications.length && !loading" description="暂无未读提醒" :image-size="70" />
        <div v-else v-loading="loading" class="notification-list">
          <article v-for="item in notifications" :key="item.id" class="notification-item">
            <div class="notification-content">
              <p class="notification-message">{{ item.message }}</p>
              <time>{{ formatDateTime(item.remind_at, timeZone) }}</time>
            </div>
            <div class="notification-actions">
              <el-button
                v-if="item.target_type !== 'custom'"
                size="small"
                text
                @click="openTarget(item)"
              >
                查看
              </el-button>
              <el-button
                size="small"
                type="primary"
                plain
                :loading="actionId === item.id"
                @click="markRead(item)"
              >
                已读
              </el-button>
            </div>
          </article>
        </div>
        <p class="panel-hint">每 30 秒自动刷新，仅显示已触发的提醒。</p>
      </section>
    </el-popover>
  </div>
</template>

<style scoped>
.notification-center { position: fixed; z-index: 1000; top: 16px; right: 20px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.load-alert { margin-bottom: 10px; }
.notification-list { display: grid; gap: 8px; max-height: 420px; overflow-y: auto; }
.notification-item { padding: 12px; border: 1px solid #ebeef5; border-radius: 8px; }
.notification-message { color: #303133; line-height: 1.5; white-space: pre-wrap; }
.notification-content time { display: block; margin-top: 5px; color: #909399; font-size: 12px; }
.notification-actions { display: flex; justify-content: flex-end; margin-top: 8px; }
.panel-hint { margin-top: 12px; color: #909399; font-size: 12px; text-align: center; }
@media (max-width: 520px) {
  .notification-center { top: 10px; right: 10px; }
}
</style>
