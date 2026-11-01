import { http } from './http'
import type { ApiResponse } from '../types/api'
import type {
  ReorderItem,
  Trip,
  TripDraft,
  TripGeneratePayload,
  TripItem,
  TripItemPayload,
  TripPage,
  TripPayload,
  TripUpdatePayload,
} from '../types/trip'

export async function listTrips(page = 1, pageSize = 12): Promise<TripPage> {
  const response = await http.get<ApiResponse<TripPage>>('/trips', {
    params: { page, page_size: pageSize },
  })
  return response.data.data
}

export async function getTrip(id: number): Promise<Trip> {
  const response = await http.get<ApiResponse<Trip>>(`/trips/${id}`)
  return response.data.data
}

export async function createTrip(data: TripPayload): Promise<Trip> {
  const response = await http.post<ApiResponse<Trip>>('/trips', data)
  return response.data.data
}

export async function updateTrip(id: number, data: TripUpdatePayload): Promise<Trip> {
  const response = await http.patch<ApiResponse<Trip>>(`/trips/${id}`, data)
  return response.data.data
}

export async function deleteTrip(id: number): Promise<void> {
  await http.delete(`/trips/${id}`)
}

export async function generateTrip(data: TripGeneratePayload): Promise<TripDraft> {
  const response = await http.post<ApiResponse<TripDraft>>('/trips/generate', data, {
    timeout: 100_000,
  })
  return response.data.data
}

export async function addTripItem(tripId: number, data: TripItemPayload): Promise<TripItem> {
  const response = await http.post<ApiResponse<TripItem>>(`/trips/${tripId}/items`, data)
  return response.data.data
}

export async function updateTripItem(
  tripId: number,
  itemId: number,
  data: Partial<TripItemPayload>,
): Promise<TripItem> {
  const response = await http.patch<ApiResponse<TripItem>>(
    `/trips/${tripId}/items/${itemId}`,
    data,
  )
  return response.data.data
}

export async function deleteTripItem(tripId: number, itemId: number): Promise<void> {
  await http.delete(`/trips/${tripId}/items/${itemId}`)
}

export async function reorderTripItems(tripId: number, items: ReorderItem[]): Promise<Trip> {
  const response = await http.put<ApiResponse<Trip>>(`/trips/${tripId}/items/reorder`, { items })
  return response.data.data
}

export async function exportTripMarkdown(id: number): Promise<Blob> {
  const response = await http.get<Blob>(`/trips/${id}/export`, {
    params: { format: 'md' },
    responseType: 'blob',
  })
  return response.data
}
