export type LLMProvider = 'mimo' | 'deepseek'

export interface GeneralSettings {
  timezone: string
  expiring_days: number
  daily_llm_call_limit: number
}

export interface LLMProviderSettings {
  provider: LLMProvider
  label: string
  base_url: string
  model: string
  configured: boolean
  source: 'user' | 'environment' | 'none'
  is_active: boolean
  key_hint: string | null
  last_tested_at: string | null
  last_test_success: boolean | null
  last_test_error: string | null
  console_url: string
}

export interface AppSettings {
  general: GeneralSettings
  active_provider: LLMProvider | null
  providers: LLMProviderSettings[]
}

export interface LLMConfigPayload {
  api_key?: string | null
  base_url?: string | null
  model?: string | null
}

export interface LLMConfigUpdate extends LLMConfigPayload {
  is_active: boolean
}

export interface LLMTestResult {
  provider: LLMProvider
  model: string
  success: boolean
  latency_ms: number
  message: string
}
