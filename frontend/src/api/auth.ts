import type { ApiResponse } from '../types/api'
import type { LoginRequest, RegisterRequest, TokenResponse, User } from '../types/auth'
import { http } from './http'

/** 所有认证请求集中在 API 层，页面和 store 不直接操作 axios。 */
export async function register(data: RegisterRequest): Promise<User> {
  const response = await http.post<ApiResponse<User>>('/auth/register', data)
  return response.data.data
}

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await http.post<ApiResponse<TokenResponse>>('/auth/login', data)
  return response.data.data
}

export async function getCurrentUser(): Promise<User> {
  const response = await http.get<ApiResponse<User>>('/auth/me')
  return response.data.data
}
