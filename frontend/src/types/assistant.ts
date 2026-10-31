export type AssistantTool =
  | 'create_todo'
  | 'create_event'
  | 'add_expense'
  | 'add_income'
  | 'add_ingredient'
  | 'save_bookmark'
  | 'create_trip'
  | 'ask_clarification'

export interface AssistantAction {
  tool: AssistantTool
  args: Record<string, unknown>
  summary: string
}

export interface ParseResponse {
  record_id: number
  actions: AssistantAction[]
  clarification: string | null
}

export interface ConfirmRequest {
  record_id: number
  actions: AssistantAction[]
}

export interface ActionResult {
  tool: AssistantTool
  ref: string
  id: number
}

export interface ConfirmResponse {
  record_id: number
  status: 'executed'
  results: ActionResult[]
}
