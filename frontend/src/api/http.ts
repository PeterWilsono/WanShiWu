import axios, { AxiosError } from 'axios'

import type { ApiResponse } from '../types/api'
import { clearAccessToken, getAccessToken } from '../utils/authStorage'

/** 页面和组件统一接收的错误类型，避免直接依赖 Axios 内部结构。 */
export class ApiError extends Error {
  code: number
  status: number | undefined
  data: unknown

  constructor(message: string, code: number, status: number | undefined, data: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.data = data
  }
}

function isApiResponse(value: unknown): value is ApiResponse<unknown> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'code' in value &&
    typeof value.code === 'number' &&
    'message' in value &&
    typeof value.message === 'string' &&
    'data' in value
  )
}

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<unknown>
    const body = axiosError.response?.data
    const status = axiosError.response?.status
    const message = isApiResponse(body)
      ? body.message
      : status
        ? axiosError.message
        : '网络连接失败，请检查后端是否已启动'
    const code = isApiResponse(body) ? body.code : status === 401 ? 40101 : 50001
    return new ApiError(message, code, status, isApiResponse(body) ? body.data : null)
  }

  if (error instanceof Error) return new ApiError(error.message, 50001, undefined)
  return new ApiError('发生未知错误', 50001, undefined)
}

function redirectToLogin(): void {
  if (window.location.pathname === '/login') return
  const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`
  window.location.replace(`/login?redirect=${encodeURIComponent(currentPath)}`)
}

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 10_000,
})

// 请求拦截器：业务 API 不必逐个手写 Authorization。
http.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.set('Authorization', `Bearer ${token}`)
  return config
})

http.interceptors.response.use(
  (response) => {
    const body: unknown = response.data
    // HTTP 200 但业务码非 0 时，也按失败交给页面处理。
    if (isApiResponse(body) && body.code !== 0) {
      if (body.code === 40101) {
        clearAccessToken()
        redirectToLogin()
      }
      return Promise.reject(new ApiError(body.message, body.code, response.status, body.data))
    }
    return response
  },
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      // 登录接口本身的 401 是「账号或密码错误」，应由登录页显示，不能刷新跳转。
      if (error.config?.url !== '/auth/login') {
        clearAccessToken()
        redirectToLogin()
      }
    }
    return Promise.reject(toApiError(error))
  },
)
