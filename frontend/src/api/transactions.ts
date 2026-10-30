import type { ApiResponse } from '../types/api'
import type {
  Transaction,
  TransactionCreateRequest,
  TransactionListQuery,
  TransactionListResponse,
  TransactionUpdateRequest,
} from '../types/transaction'
import { http } from './http'

export async function listTransactions(
  params: TransactionListQuery = {},
): Promise<TransactionListResponse> {
  const response = await http.get<ApiResponse<TransactionListResponse>>('/transactions', { params })
  return response.data.data
}

export async function createTransaction(data: TransactionCreateRequest): Promise<Transaction> {
  const response = await http.post<ApiResponse<Transaction>>('/transactions', data)
  return response.data.data
}

export async function getTransaction(id: number): Promise<Transaction> {
  const response = await http.get<ApiResponse<Transaction>>(`/transactions/${id}`)
  return response.data.data
}

export async function updateTransaction(
  id: number,
  data: TransactionUpdateRequest,
): Promise<Transaction> {
  const response = await http.patch<ApiResponse<Transaction>>(`/transactions/${id}`, data)
  return response.data.data
}

export async function deleteTransaction(id: number): Promise<void> {
  await http.delete<ApiResponse<null>>(`/transactions/${id}`)
}
