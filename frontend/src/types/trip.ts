export type TripStatus = 'draft' | 'confirmed'
export type TripGeneratedBy = 'manual' | 'ai'

export interface TripItemPayload {
  day_index: number
  sort_order?: number | null
  start_time?: string | null
  place: string
  note?: string | null
  cost_cents?: number
}

export interface TripItem extends Required<Omit<TripItemPayload, 'sort_order'>> {
  id: number
  trip_id: number
  sort_order: number
  created_at: string
  updated_at: string
}

export interface TripPayload {
  title: string
  destination: string
  start_date?: string | null
  days: number
  budget_cents?: number | null
  preferences?: string | null
  generated_by?: TripGeneratedBy
  status?: TripStatus
  items?: TripItemPayload[]
}

export type TripUpdatePayload = Partial<Omit<TripPayload, 'items' | 'generated_by'>>

export interface DaySummary {
  day_index: number
  date: string | null
  items: TripItem[]
  subtotal_cents: number
}

export interface Trip {
  id: number
  title: string
  destination: string
  start_date: string | null
  days: number
  budget_cents: number | null
  preferences: string | null
  generated_by: TripGeneratedBy
  status: TripStatus
  items: TripItem[]
  daily_summaries: DaySummary[]
  planned_cents: number
  budget_remaining_cents: number | null
  over_budget: boolean
  created_at: string
  updated_at: string
}

export interface TripPage {
  items: Trip[]
  total: number
  page: number
  page_size: number
}

export interface TripGeneratePayload {
  destination: string
  start_date?: string | null
  days: number
  budget_cents?: number | null
  preferences?: string | null
}

export interface TripDraft {
  draft: Required<Omit<TripPayload, 'start_date' | 'budget_cents' | 'preferences'>> & {
    start_date: string | null
    budget_cents: number | null
    preferences: string | null
  }
  planned_cents: number
  budget_remaining_cents: number | null
  over_budget: boolean
}

export interface ReorderItem {
  id: number
  day_index: number
  sort_order: number
}
