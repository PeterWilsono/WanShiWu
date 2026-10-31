import type { TransactionType } from './category'

export interface CategoryStats {
  category_id: number
  category_name: string
  type: TransactionType
  amount_cents: number
}

export interface MonthlyStats {
  month: string
  income_cents: number
  expense_cents: number
  balance_cents: number
  categories: CategoryStats[]
}

export interface DailyExpenseStats {
  date: string
  expense_cents: number
}

export interface DailyStats {
  month: string
  days: DailyExpenseStats[]
}
