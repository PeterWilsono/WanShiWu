<script setup lang="ts">
import { ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getSettings } from '../api/settings'
import AppIcon from '../components/AppIcon.vue'
import { useAuthStore } from '../stores/auth'
import type { AppSettings } from '../types/settings'

const router = useRouter()
const authStore = useAuthStore()
const settings = ref<AppSettings | null>(null)
const currentProvider = computed(() =>
  settings.value?.providers.find((provider) => provider.is_active) ?? null,
)
const createdAt = computed(() => {
  const value = authStore.user?.created_at
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long' }).format(new Date(value)) : '—'
})

async function logout(): Promise<void> {
  try {
    await ElMessageBox.confirm('退出后需要重新输入用户名和密码。', '退出登录', {
      confirmButtonText: '退出登录',
      cancelButtonText: '留在这里',
    })
  } catch {
    return
  }
  authStore.logout()
  await router.push({ name: 'login' })
}

onMounted(async () => {
  try {
    settings.value = await getSettings()
  } catch {
    // 账号资料仍可查看；设置页会提供更完整的加载与重试提示。
  }
})
</script>

<template>
  <main class="profile-page">
    <section class="profile-hero">
      <div class="profile-avatar" aria-hidden="true">{{ authStore.user?.username.slice(0, 1).toUpperCase() }}</div>
      <div>
        <p class="page-eyebrow">MY WANSHIWU</p>
        <h1>{{ authStore.user?.username }}</h1>
        <p>从 {{ createdAt }} 开始，收好自己的生活。</p>
      </div>
      <span class="profile-seal">我的</span>
    </section>

    <section class="profile-section">
      <div class="section-heading">
        <div><p class="page-eyebrow">偏好与账户</p><h2>让万事屋更懂你</h2></div>
      </div>
      <div class="settings-grid">
        <button class="settings-card settings-card--featured" @click="router.push({ name: 'settings', query: { tab: 'ai' } })">
          <span class="settings-card__icon"><AppIcon name="sparkle" :size="23" /></span>
          <span class="settings-card__body">
            <small>AI 模型</small>
            <strong>{{ currentProvider?.label || '尚未配置模型' }}</strong>
            <span>{{ currentProvider?.model || '配置 MiMo 或 DeepSeek 后，即可使用 AI 功能' }}</span>
          </span>
          <span class="model-status" :class="{ ready: currentProvider }">{{ currentProvider ? '使用中' : '待配置' }}</span>
          <AppIcon name="arrow" :size="18" />
        </button>

        <button class="settings-card" @click="router.push({ name: 'settings', query: { tab: 'general' } })">
          <span class="settings-card__icon"><AppIcon name="settings" :size="23" /></span>
          <span class="settings-card__body"><small>通用设置</small><strong>时区与提醒偏好</strong><span>临期天数、每日 AI 调用上限</span></span>
          <AppIcon name="arrow" :size="18" />
        </button>

        <button class="settings-card" @click="router.push({ name: 'categories' })">
          <span class="settings-card__icon"><AppIcon name="wallet" :size="23" /></span>
          <span class="settings-card__body"><small>账目偏好</small><strong>分类管理</strong><span>整理属于自己的收入与支出分类</span></span>
          <AppIcon name="arrow" :size="18" />
        </button>
      </div>
    </section>

    <section class="account-panel">
      <div><small>登录账号</small><strong>{{ authStore.user?.username }}</strong></div>
      <div><small>所在时区</small><strong>{{ settings?.general.timezone || authStore.user?.timezone }}</strong></div>
      <button class="logout-button" @click="logout"><AppIcon name="logout" :size="17" />退出登录</button>
    </section>
  </main>
</template>

<style scoped>
.profile-page { width: min(1060px, 100%); margin: 0 auto; padding: 54px 32px 80px; }
.profile-hero { position: relative; display: flex; align-items: center; gap: 24px; overflow: hidden; padding: 38px 40px; border: 1px solid var(--line-soft); border-radius: 4px 28px 4px 4px; background: var(--paper-light); box-shadow: var(--shadow-soft); }
.profile-avatar { display: grid; width: 82px; height: 82px; flex: 0 0 auto; place-items: center; border: 1px solid var(--line); border-radius: 50%; color: var(--paper-light); background: var(--ink); font-family: var(--font-display); font-size: 34px; }
.page-eyebrow { margin: 0 0 7px; color: var(--vermilion); font-size: 10px; font-weight: 700; letter-spacing: .22em; }
.profile-hero h1 { margin: 0 0 7px; font-family: var(--font-display); font-size: 38px; font-weight: 600; }
.profile-hero p:last-child { margin: 0; color: var(--ink-muted); font-size: 14px; }
.profile-seal { position: absolute; right: 34px; color: var(--paper-deep); font-family: var(--font-display); font-size: 74px; font-weight: 700; letter-spacing: .12em; pointer-events: none; }
.profile-section { margin-top: 46px; }
.section-heading h2 { margin: 0 0 20px; font-family: var(--font-display); font-size: 25px; font-weight: 600; }
.settings-grid { display: grid; gap: 12px; }
.settings-card { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 18px; width: 100%; padding: 22px 24px; border: 1px solid var(--line-soft); border-radius: 3px 16px 3px 3px; color: var(--ink); background: var(--paper-light); cursor: pointer; text-align: left; transition: border-color .2s ease, box-shadow .2s ease, transform .2s ease; }
.settings-card:hover { border-color: var(--line); box-shadow: var(--shadow-soft); transform: translateY(-2px); }
.settings-card--featured { grid-template-columns: auto minmax(0, 1fr) auto auto; border-color: color-mix(in srgb, var(--vermilion) 24%, var(--line-soft)); }
.settings-card__icon { display: grid; width: 46px; height: 46px; place-items: center; border-radius: 13px 13px 13px 4px; color: var(--vermilion); background: var(--paper-deep); }
.settings-card__body { display: grid; gap: 5px; }
.settings-card__body small { color: var(--ink-muted); font-size: 11px; letter-spacing: .12em; }
.settings-card__body strong { font-family: var(--font-display); font-size: 19px; font-weight: 600; }
.settings-card__body > span { color: var(--ink-secondary); font-size: 13px; }
.model-status { padding: 4px 9px; border-radius: 99px; color: var(--ink-muted); background: var(--paper-deep); font-size: 11px; white-space: nowrap; }
.model-status.ready { color: var(--pine); background: color-mix(in srgb, var(--pine) 10%, transparent); }
.account-panel { display: flex; align-items: center; gap: 48px; margin-top: 32px; padding: 24px 4px; border-top: 1px solid var(--line-soft); }
.account-panel > div { display: grid; gap: 5px; }
.account-panel small { color: var(--ink-muted); font-size: 11px; }
.account-panel strong { font-size: 14px; font-weight: 500; }
.logout-button { display: flex; align-items: center; gap: 7px; margin-left: auto; padding: 9px 0; border: 0; color: var(--ink-muted); background: transparent; cursor: pointer; }
.logout-button:hover { color: var(--vermilion); }
@media (max-width: 640px) {
  .profile-page { padding: 32px 18px 60px; }
  .profile-hero { padding: 28px 24px; gap: 17px; }
  .profile-avatar { width: 62px; height: 62px; font-size: 27px; }
  .profile-hero h1 { font-size: 30px; }
  .profile-seal { display: none; }
  .settings-card, .settings-card--featured { grid-template-columns: auto minmax(0, 1fr) auto; padding: 18px; gap: 13px; }
  .model-status { display: none; }
  .settings-card__body > span { line-height: 1.5; }
  .account-panel { flex-wrap: wrap; gap: 22px 36px; }
  .logout-button { width: 100%; margin-left: 0; }
}
</style>
