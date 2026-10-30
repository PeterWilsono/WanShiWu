/** 与后端 app/modules/life/schemas.py 对应的待办类型。 */
export type TodoStatus = 'pending' | 'done' | 'cancelled'
export type Recurrence = 'none' | 'daily' | 'weekly' | 'monthly'
export type TodoSort = 'due_at' | 'created_at' | 'priority'
export type SortOrder = 'asc' | 'desc'

export interface Todo {
  id: number
  title: string
  note: string | null
  /** ISO 8601 字符串；业务展示时再按用户时区转换。 */
  due_at: string | null
  priority: 1 | 2 | 3
  status: TodoStatus
  completed_at: string | null
  recurrence: Recurrence
  tags: string[]
  created_at: string
  updated_at: string
}

export interface TodoCreateRequest {
  title: string
  note?: string | null
  due_at?: string | null
  priority?: 1 | 2 | 3
  recurrence?: Recurrence
  tags?: string[]
}

/** PATCH 只提交需要修改的字段；note/due_at 显式传 null 表示清空。 */
export interface TodoUpdateRequest {
  title?: string
  note?: string | null
  due_at?: string | null
  priority?: 1 | 2 | 3
  status?: TodoStatus
  recurrence?: Recurrence
  tags?: string[]
}

export interface TodoListQuery {
  page?: number
  page_size?: number
  status?: TodoStatus
  due_after?: string
  due_before?: string
  tag?: string
  sort?: TodoSort
  order?: SortOrder
}

export interface TodoListResponse {
  items: Todo[]
  total: number
  page: number
  page_size: number
}

export interface TodoCompleteResponse {
  todo: Todo
  next_todo: Todo | null
}
