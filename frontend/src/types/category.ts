export type TransactionType = 'income' | 'expense'

export interface Category {
  id: number
  name: string
  type: TransactionType
  icon: string | null
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface CategoryCreateRequest {
  name: string
  type: TransactionType
  icon?: string | null
}

/** 分类类型和内置标记不可通过 PATCH 修改。 */
export interface CategoryUpdateRequest {
  name?: string
  icon?: string | null
}
