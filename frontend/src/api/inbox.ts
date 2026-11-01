import { http } from './http'
import type { ApiResponse } from '../types/api'
import type {
  Bookmark,
  BookmarkPage,
  BookmarkPayload,
  BookmarkQuery,
  BookmarkUpdate,
  Tag,
  WeeklyDigestPage,
} from '../types/inbox'

export async function listBookmarks(params: BookmarkQuery): Promise<BookmarkPage> {
  const response = await http.get<ApiResponse<BookmarkPage>>('/bookmarks', { params })
  return response.data.data
}

export async function searchBookmarks(
  q: string,
  page = 1,
  pageSize = 20,
): Promise<BookmarkPage> {
  const response = await http.get<ApiResponse<BookmarkPage>>('/bookmarks/search', {
    params: { q, page, page_size: pageSize },
  })
  return response.data.data
}

export async function createBookmark(data: BookmarkPayload): Promise<Bookmark> {
  const response = await http.post<ApiResponse<Bookmark>>('/bookmarks', data)
  return response.data.data
}

export async function updateBookmark(id: number, data: BookmarkUpdate): Promise<Bookmark> {
  const response = await http.patch<ApiResponse<Bookmark>>(`/bookmarks/${id}`, data)
  return response.data.data
}

export async function deleteBookmark(id: number): Promise<void> {
  await http.delete(`/bookmarks/${id}`)
}

export async function retryBookmark(id: number): Promise<Bookmark> {
  const response = await http.post<ApiResponse<Bookmark>>(`/bookmarks/${id}/retry`)
  return response.data.data
}

export async function updateBookmarkContent(id: number, content: string): Promise<Bookmark> {
  const response = await http.put<ApiResponse<Bookmark>>(
    `/bookmarks/${id}/content`,
    { content },
    { timeout: 100_000 },
  )
  return response.data.data
}

export async function listTags(): Promise<Tag[]> {
  const response = await http.get<ApiResponse<{ items: Tag[] }>>('/tags')
  return response.data.data.items
}

export async function listWeeklyDigests(page = 1, pageSize = 10): Promise<WeeklyDigestPage> {
  const response = await http.get<ApiResponse<WeeklyDigestPage>>('/inbox/weekly-digests', {
    params: { page, page_size: pageSize },
  })
  return response.data.data
}
