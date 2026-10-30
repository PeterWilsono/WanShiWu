import type { ApiResponse } from '../types/api'
import type {
  Category,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  TransactionType,
} from '../types/category'
import { http } from './http'

export async function listCategories(type?: TransactionType): Promise<Category[]> {
  const response = await http.get<ApiResponse<Category[]>>('/categories', {
    params: type ? { type } : undefined,
  })
  return response.data.data
}

export async function createCategory(data: CategoryCreateRequest): Promise<Category> {
  const response = await http.post<ApiResponse<Category>>('/categories', data)
  return response.data.data
}

export async function updateCategory(id: number, data: CategoryUpdateRequest): Promise<Category> {
  const response = await http.patch<ApiResponse<Category>>(`/categories/${id}`, data)
  return response.data.data
}

export async function deleteCategory(id: number): Promise<void> {
  await http.delete<ApiResponse<null>>(`/categories/${id}`)
}
