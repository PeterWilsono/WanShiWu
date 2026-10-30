import type { ApiResponse } from '../types/api'
import type {
  Event,
  EventCreateRequest,
  EventListQuery,
  EventListResponse,
  EventUpdateRequest,
} from '../types/event'
import { http } from './http'

/** 日程接口集中在这里，页面不直接处理 URL、统一响应或 Axios。 */
export async function listEvents(params: EventListQuery = {}): Promise<EventListResponse> {
  const response = await http.get<ApiResponse<EventListResponse>>('/events', { params })
  return response.data.data
}

export async function createEvent(data: EventCreateRequest): Promise<Event> {
  const response = await http.post<ApiResponse<Event>>('/events', data)
  return response.data.data
}

export async function getEvent(id: number): Promise<Event> {
  const response = await http.get<ApiResponse<Event>>(`/events/${id}`)
  return response.data.data
}

export async function updateEvent(id: number, data: EventUpdateRequest): Promise<Event> {
  const response = await http.patch<ApiResponse<Event>>(`/events/${id}`, data)
  return response.data.data
}

export async function deleteEvent(id: number): Promise<void> {
  await http.delete<ApiResponse<null>>(`/events/${id}`)
}
