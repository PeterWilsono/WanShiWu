/** 与后端 PROJECT_SPEC.md 8.2 对应的统一响应结构。 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}
