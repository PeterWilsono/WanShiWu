/** 与后端 app/modules/auth/schemas.py 保持一致。 */
export interface User {
  id: number
  username: string
  timezone: string
  settings_json: Record<string, unknown>
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
