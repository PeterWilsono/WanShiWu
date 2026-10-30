import type { Category, TransactionType } from './category'

export type TransactionSource = 'manual' | 'assistant' | 'pantry' | 'trip'

export interface Transaction {
  id: number
  amount_cents: number
  type: TransactionType
  category_id: number
  category: Category
  note: string | null
  occurred_at: string
  source: TransactionSource
  created_at: string
  updated_at: string
}

export interface TransactionCreateRequest {
  amount_cents: number
  type: TransactionType
  category_id: number
  note?: string | null
  occurred_at: string
  source?: TransactionSource
}

/** 字段未传表示保持原值；只有备注允许显式传 null 清空。 */
export interface TransactionUpdateRequest {
  amount_cents?: number
  type?: TransactionType
  category_id?: number
  note?: string | null
  occurred_at?: string
  source?: TransactionSource
}

export interface TransactionListQuery {
  page?: number
  page_size?: number
  /** YYYY-MM，由后端按当前用户时区计算自然月边界。 */
  month?: string
  category_id?: number
  type?: TransactionType
  sort?: 'occurred_at' | 'amount_cents' | 'created_at'
  order?: 'asc' | 'desc'
}

export interface TransactionListResponse {
  items: Transaction[]
  total: number
  page: number
  page_size: number
}
