/** 只格式化展示文本；接口和计算仍使用后端返回的十进制字符串。 */
export function formatQuantity(value: string): string {
  const [integer, fraction] = value.split('.')
  if (!fraction) return value
  const trimmed = fraction.replace(/0+$/, '')
  return trimmed ? `${integer}.${trimmed}` : integer
}
