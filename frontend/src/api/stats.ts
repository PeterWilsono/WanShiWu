import type { ApiResponse } from '../types/api'
import type { DailyStats, MonthlyStats } from '../types/stats'
import { http } from './http'

export async function getMonthlyStats(month: string): Promise<MonthlyStats> {
  const response = await http.get<ApiResponse<MonthlyStats>>('/stats/monthly', {
    params: { month },
  })
  return response.data.data
}

export async function getDailyStats(month: string): Promise<DailyStats> {
  const response = await http.get<ApiResponse<DailyStats>>('/stats/daily', {
    params: { month },
  })
  return response.data.data
}
