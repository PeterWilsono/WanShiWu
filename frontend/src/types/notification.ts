export type NotificationTargetType = 'event' | 'todo' | 'custom'

export interface AppNotification {
  id: number
  target_type: NotificationTargetType
  target_id: number | null
  remind_at: string
  message: string
  fired_at: string
  read_at: string | null
}

export interface NotificationListResponse {
  items: AppNotification[]
  total: number
  unread_count: number
  page: number
  page_size: number
}
