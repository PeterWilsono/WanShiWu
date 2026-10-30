/** 与后端 app/modules/life/schemas.py 对应的日程类型。 */
export interface Event {
  id: number
  title: string
  /** ISO 8601 UTC 字符串；展示时再按用户时区转换。 */
  start_at: string
  /** null 表示只有一个开始时间点的日程。 */
  end_at: string | null
  all_day: boolean
  location: string | null
  /** 提前多少分钟提醒；null 表示未设置。 */
  remind_before_min: number | null
  note: string | null
  created_at: string
  updated_at: string
}

export interface EventCreateRequest {
  title: string
  /** 必须包含时区偏移，例如 2026-11-10T09:00:00+08:00。 */
  start_at: string
  end_at?: string | null
  all_day?: boolean
  location?: string | null
  remind_before_min?: number | null
  note?: string | null
}

/** PATCH 只提交需要修改的字段；可空字段显式传 null 表示清空。 */
export interface EventUpdateRequest {
  title?: string
  start_at?: string
  end_at?: string | null
  all_day?: boolean
  location?: string | null
  remind_before_min?: number | null
  note?: string | null
}

export interface EventListQuery {
  page?: number
  page_size?: number
  /** 查询窗口开始，返回与该窗口重叠的日程。 */
  range_start?: string
  /** 查询窗口结束，返回与该窗口重叠的日程。 */
  range_end?: string
}

export interface EventListResponse {
  items: Event[]
  total: number
  page: number
  page_size: number
}
