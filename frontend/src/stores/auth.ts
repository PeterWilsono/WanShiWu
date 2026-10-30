import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '../api/auth'
import type { LoginRequest, RegisterRequest, User } from '../types/auth'
import { clearAccessToken, getAccessToken, saveAccessToken } from '../utils/authStorage'

/** 全局只保存认证所需状态；页面列表数据不放进 Pinia（PROJECT_SPEC.md 11.2）。 */
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getAccessToken())
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => token.value !== null)

  function logout(): void {
    clearAccessToken()
    token.value = null
    user.value = null
  }

  async function fetchCurrentUser(): Promise<User | null> {
    if (!token.value) {
      user.value = null
      return null
    }

    try {
      user.value = await authApi.getCurrentUser()
      return user.value
    } catch (error) {
      // 令牌无效或后端无法确认用户时，不保留看似已登录的本地状态。
      logout()
      throw error
    }
  }

  async function login(credentials: LoginRequest): Promise<User> {
    loading.value = true
    try {
      const result = await authApi.login(credentials)
      saveAccessToken(result.access_token)
      token.value = result.access_token
      const currentUser = await fetchCurrentUser()
      if (!currentUser) throw new Error('登录后未能获取当前用户')
      return currentUser
    } catch (error) {
      logout()
      throw error
    } finally {
      loading.value = false
    }
  }

  // 注册不自动登录，登录页可以明确引导用户再执行一次登录流程。
  async function register(data: RegisterRequest): Promise<User> {
    return authApi.register(data)
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    login,
    register,
    fetchCurrentUser,
    logout,
  }
})
