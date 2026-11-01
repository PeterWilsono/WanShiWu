<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import AppIcon from './AppIcon.vue'
import NotificationCenter from './NotificationCenter.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const menuOpen = ref(false)

const navigation = [
  { name: 'home', label: '起居', icon: 'home' },
  { name: 'todos', label: '待办', icon: 'check' },
  { name: 'calendar', label: '日历', icon: 'calendar' },
  { name: 'transactions', label: '账目', icon: 'wallet' },
  { name: 'pantry', label: '食材', icon: 'pantry' },
  { name: 'inbox', label: '收藏', icon: 'bookmark' },
  { name: 'trip', label: '旅行', icon: 'transport' },
]

function isActive(name: string): boolean {
  if (name === 'calendar') return ['calendar', 'events'].includes(String(route.name))
  if (name === 'transactions') return ['transactions', 'stats', 'categories'].includes(String(route.name))
  if (name === 'trip') return ['trip', 'trip-detail'].includes(String(route.name))
  return route.name === name
}

async function navigate(name: string): Promise<void> {
  menuOpen.value = false
  await router.push({ name })
}

async function logout(): Promise<void> {
  authStore.logout()
  await router.push({ name: 'login' })
}
</script>

<template>
  <header class="app-header">
    <div class="app-header__inner">
      <button class="brand" aria-label="返回万事屋首页" @click="navigate('home')">
        <span class="brand__seal" aria-hidden="true">万</span>
        <span class="brand__type"><strong>万事屋</strong><small>WANSHIWU</small></span>
      </button>

      <nav class="desktop-nav" aria-label="主导航">
        <button
          v-for="item in navigation"
          :key="item.name"
          :class="{ active: isActive(item.name) }"
          @click="navigate(item.name)"
        >
          {{ item.label }}
        </button>
      </nav>

      <div class="app-header__actions">
        <NotificationCenter />
        <el-dropdown trigger="click">
          <button class="user-chip" aria-label="账户菜单">
            <span class="user-chip__avatar">{{ authStore.user?.username.slice(0, 1).toUpperCase() }}</span>
            <span class="user-chip__name">{{ authStore.user?.username }}</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="navigate('profile')">我的</el-dropdown-item>
              <el-dropdown-item @click="navigate('settings')">设置</el-dropdown-item>
              <el-dropdown-item @click="navigate('categories')">分类管理</el-dropdown-item>
              <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <button class="menu-button" :aria-expanded="menuOpen" aria-label="展开导航" @click="menuOpen = !menuOpen">
          <span /><span />
        </button>
      </div>
    </div>

    <Transition name="menu-reveal">
      <nav v-if="menuOpen" class="mobile-menu" aria-label="移动端主导航">
        <button
          v-for="item in navigation"
          :key="item.name"
          :class="{ active: isActive(item.name) }"
          @click="navigate(item.name)"
        >
          <AppIcon :name="item.icon" :size="18" />{{ item.label }}<AppIcon name="arrow" :size="16" />
        </button>
        <button @click="navigate('profile')"><AppIcon name="user" :size="18" />我的<AppIcon name="arrow" :size="16" /></button>
        <button @click="navigate('settings')"><AppIcon name="settings" :size="18" />设置<AppIcon name="arrow" :size="16" /></button>
        <button @click="navigate('categories')"><AppIcon name="wallet" :size="18" />分类管理<AppIcon name="arrow" :size="16" /></button>
      </nav>
    </Transition>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  z-index: 1000;
  top: 0;
  border-bottom: 1px solid var(--line-soft);
  background: color-mix(in srgb, var(--paper) 88%, transparent);
  backdrop-filter: blur(20px) saturate(1.2);
}
.app-header__inner {
  display: flex;
  width: min(1440px, 100%);
  height: 84px;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  margin: 0 auto;
  padding: 0 40px;
}
.brand { display: flex; align-items: center; gap: 12px; padding: 0; border: 0; color: var(--ink); background: transparent; cursor: pointer; text-align: left; }
.brand__seal { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 11px 11px 11px 3px; color: #fffaf0; background: var(--vermilion); box-shadow: 0 6px 16px rgb(177 71 46 / 18%); font-family: var(--font-display); font-size: 22px; transform: rotate(-3deg); transition: transform .3s ease; }
.brand:hover .brand__seal { transform: rotate(3deg) translateY(-2px); }
.brand__type { display: grid; gap: 1px; }
.brand__type strong { font-family: var(--font-display); font-size: 20px; font-weight: 700; letter-spacing: .12em; }
.brand__type small { color: var(--ink-muted); font-size: 8px; font-weight: 600; letter-spacing: .28em; }
.desktop-nav { display: flex; align-self: stretch; gap: 32px; }
.desktop-nav button { position: relative; padding: 2px 0 0; border: 0; color: var(--ink-secondary); background: transparent; cursor: pointer; font-size: 14px; letter-spacing: .08em; transition: color .2s ease; }
.desktop-nav button::after { position: absolute; right: 0; bottom: 19px; left: 0; height: 2px; border-radius: 2px; background: var(--vermilion); content: ''; transform: scaleX(0); transform-origin: right; transition: transform .25s ease; }
.desktop-nav button:hover, .desktop-nav button.active { color: var(--ink); }
.desktop-nav button.active::after { transform: scaleX(1); transform-origin: left; }
.app-header__actions { display: flex; align-items: center; gap: 14px; }
.user-chip { display: flex; align-items: center; gap: 9px; padding: 4px 8px 4px 4px; border: 0; border-radius: 99px; color: var(--ink); background: transparent; cursor: pointer; transition: background .2s ease; }
.user-chip:hover { background: var(--paper-deep); }
.user-chip__avatar { display: grid; width: 32px; height: 32px; place-items: center; border: 1px solid var(--line); border-radius: 50%; background: var(--paper-light); font-family: var(--font-display); font-size: 15px; }
.user-chip__name { max-width: 90px; overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.menu-button { display: none; width: 38px; height: 38px; padding: 10px; border: 0; border-radius: 50%; background: var(--paper-deep); cursor: pointer; }
.menu-button span { display: block; width: 100%; height: 1px; margin: 5px 0; background: var(--ink); }
.mobile-menu { display: none; }
.menu-reveal-enter-active, .menu-reveal-leave-active { transition: opacity .2s ease, transform .2s ease; }
.menu-reveal-enter-from, .menu-reveal-leave-to { opacity: 0; transform: translateY(-8px); }
@media (max-width: 960px) {
  .app-header__inner { height: 72px; padding: 0 24px; }
  .desktop-nav { display: none; }
  .menu-button { display: block; }
  .mobile-menu { display: grid; padding: 8px 24px 20px; border-top: 1px solid var(--line-soft); background: var(--paper); }
  .mobile-menu button { display: grid; grid-template-columns: 24px 1fr auto; align-items: center; gap: 12px; padding: 14px 4px; border: 0; border-bottom: 1px solid var(--line-soft); color: var(--ink-secondary); background: transparent; text-align: left; }
  .mobile-menu button.active { color: var(--vermilion); }
}
@media (max-width: 520px) {
  .app-header__inner { padding: 0 18px; }
  .brand__type small, .user-chip__name { display: none; }
  .brand__type strong { font-size: 18px; }
  .app-header__actions { gap: 6px; }
  .user-chip { padding-right: 4px; }
  .mobile-menu { padding-right: 18px; padding-left: 18px; }
}
</style>
