import type { ApiResponse } from '../types/api'
import type { ConfirmRequest, ConfirmResponse, ParseResponse } from '../types/assistant'
import { http } from './http'

/** 模型调用可能重试，不能用普通业务接口的 10 秒超时提前中断。 */
export async function parseAssistant(text: string): Promise<ParseResponse> {
  const response = await http.post<ApiResponse<ParseResponse>>(
    '/assistant/parse',
    { text },
    { timeout: 100_000 },
  )
  return response.data.data
}

export async function confirmAssistant(data: ConfirmRequest): Promise<ConfirmResponse> {
  const response = await http.post<ApiResponse<ConfirmResponse>>('/assistant/confirm', data)
  return response.data.data
}

export async function cancelAssistantRecord(recordId: number): Promise<void> {
  await http.post<ApiResponse<unknown>>(`/assistant/records/${recordId}/cancel`)
}
