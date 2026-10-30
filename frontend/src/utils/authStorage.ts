/**
 * Token 的唯一存储入口。
 *
 * Axios 和 Pinia 都依赖这个独立模块，避免 http -> store -> api -> http 的循环依赖。
 */
const ACCESS_TOKEN_KEY = 'wanshiwu.access_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function saveAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}
