export type BookmarkStatus = 'pending' | 'processing' | 'success' | 'failed'
export type TagSource = 'manual' | 'ai'

export interface BookmarkTag {
  id: number
  name: string
  source: TagSource
}

export interface Tag {
  id: number
  name: string
}

export interface Bookmark {
  id: number
  url: string
  title: string | null
  summary: string | null
  content: string | null
  status: BookmarkStatus
  fail_reason: string | null
  note: string | null
  source_domain: string | null
  fetched_at: string | null
  tags: BookmarkTag[]
  created_at: string
  updated_at: string
}

export interface BookmarkPayload {
  url: string
  title?: string | null
  note?: string | null
  tags: string[]
}

export interface BookmarkUpdate {
  title?: string | null
  note?: string | null
  tags?: string[]
}

export interface BookmarkQuery {
  page?: number
  page_size?: number
  status?: BookmarkStatus
  tag?: string
}

export interface BookmarkPage {
  items: Bookmark[]
  total: number
  page: number
  page_size: number
}

export interface WeeklyDigest {
  id: number
  week_start: string
  content_md: string
  bookmark_count: number
  created_at: string
}

export interface WeeklyDigestPage {
  items: WeeklyDigest[]
  total: number
  page: number
  page_size: number
}
