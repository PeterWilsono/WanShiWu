import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0, behavior: 'smooth' }),
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
      path: '/calendar',
      name: 'calendar',
      component: () => import('../views/CalendarView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/stats',
      name: 'stats',
      component: () => import('../views/StatsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pantry',
      name: 'pantry',
      component: () => import('../views/PantryView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/inbox',
      name: 'inbox',
      component: () => import('../views/InboxView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/trip',
      name: 'trip',
      component: () => import('../views/TripView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/trip/:id',
      name: 'trip-detail',
      component: () => import('../views/TripDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/me',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings/categories',
      name: 'categories',
      component: () => import('../views/CategoryView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
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
