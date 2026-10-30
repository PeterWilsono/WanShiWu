import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      path: '/todos',
      name: 'todos',
      component: () => import('../views/TodoView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/events',
      name: 'events',
      component: () => import('../views/EventView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: () => import('../views/TransactionView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { guestOnly: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (to.meta.guestOnly) {
    if (!authStore.isAuthenticated) return true
    if (!authStore.user) {
      try {
        await authStore.fetchCurrentUser()
      } catch {
        // 本地 Token 已失效，store 会清理登录状态，允许进入登录页。
        return true
      }
    }
    return { name: 'home' }
  }

  if (!to.meta.requiresAuth) return true

  if (!authStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (!authStore.user) {
    try {
      await authStore.fetchCurrentUser()
    } catch {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }

  return true
})

export default router
