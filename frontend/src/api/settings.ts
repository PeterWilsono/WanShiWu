import type { ApiResponse } from '../types/api'
import type {
  AppSettings,
  GeneralSettings,
  LLMConfigPayload,
  LLMConfigUpdate,
  LLMProvider,
  LLMTestResult,
} from '../types/settings'
import { http } from './http'

export async function getSettings(): Promise<AppSettings> {
  const response = await http.get<ApiResponse<AppSettings>>('/settings')
  return response.data.data
}

export async function updateGeneralSettings(data: GeneralSettings): Promise<GeneralSettings> {
  const response = await http.put<ApiResponse<GeneralSettings>>('/settings/general', data)
  return response.data.data
}

export async function updateLLMConfig(
  provider: LLMProvider,
  data: LLMConfigUpdate,
): Promise<AppSettings> {
  const response = await http.put<ApiResponse<AppSettings>>(`/settings/llm/${provider}`, data)
  return response.data.data
}

export async function testLLMConnection(
  provider: LLMProvider,
  data: LLMConfigPayload,
): Promise<LLMTestResult> {
  const response = await http.post<ApiResponse<LLMTestResult>>(
    `/settings/llm/${provider}/test`,
    data,
    { timeout: 45_000 },
  )
  return response.data.data
}

export async function deleteLLMConfig(provider: LLMProvider): Promise<AppSettings> {
  const response = await http.delete<ApiResponse<AppSettings>>(`/settings/llm/${provider}`)
  return response.data.data
}
