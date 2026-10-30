import type { ApiResponse } from '../types/api'
import type { AppNotification, NotificationListResponse } from '../types/notification'
import { http } from './http'

export async function listUnreadNotifications(
  page = 1,
  pageSize = 20,
): Promise<NotificationListResponse> {
  const response = await http.get<ApiResponse<NotificationListResponse>>('/notifications', {
    params: { unread: true, page, page_size: pageSize },
  })
  return response.data.data
}

export async function markNotificationRead(id: number): Promise<AppNotification> {
  const response = await http.post<ApiResponse<AppNotification>>(`/notifications/${id}/read`)
  return response.data.data
}
