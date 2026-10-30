import type { ApiResponse } from '../types/api'
import type {
  Todo,
  TodoCompleteResponse,
  TodoCreateRequest,
  TodoListQuery,
  TodoListResponse,
  TodoUpdateRequest,
} from '../types/todo'
import { http } from './http'

/** 待办接口集中在这里，页面不直接处理 URL、统一响应或 Axios。 */
export async function listTodos(params: TodoListQuery = {}): Promise<TodoListResponse> {
  const response = await http.get<ApiResponse<TodoListResponse>>('/todos', { params })
  return response.data.data
}

export async function createTodo(data: TodoCreateRequest): Promise<Todo> {
  const response = await http.post<ApiResponse<Todo>>('/todos', data)
  return response.data.data
}

export async function getTodo(id: number): Promise<Todo> {
  const response = await http.get<ApiResponse<Todo>>(`/todos/${id}`)
  return response.data.data
}

export async function updateTodo(id: number, data: TodoUpdateRequest): Promise<Todo> {
  const response = await http.patch<ApiResponse<Todo>>(`/todos/${id}`, data)
  return response.data.data
}

export async function deleteTodo(id: number): Promise<void> {
  await http.delete<ApiResponse<null>>(`/todos/${id}`)
}

export async function completeTodo(id: number): Promise<TodoCompleteResponse> {
  const response = await http.post<ApiResponse<TodoCompleteResponse>>(`/todos/${id}/complete`)
  return response.data.data
}
