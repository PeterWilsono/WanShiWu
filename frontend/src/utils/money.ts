/** 金额在 API 与数据库中始终是整数分，只有输入和展示时使用元。 */
export function yuanToCents(value: string): number | null {
  const normalized = value.trim()
  const match = /^(0|[1-9]\d*)(?:\.(\d{1,2}))?$/.exec(normalized)
  if (!match) return null

  const cents = Number(match[1]) * 100 + Number((match[2] || '').padEnd(2, '0') || 0)
  return Number.isSafeInteger(cents) && cents > 0 ? cents : null
}

export function centsToYuanInput(cents: number): string {
  if (!Number.isSafeInteger(cents)) throw new Error('金额必须是安全整数分')
  const sign = cents < 0 ? '-' : ''
  const absolute = Math.abs(cents)
  return `${sign}${Math.floor(absolute / 100)}.${String(absolute % 100).padStart(2, '0')}`
}

export function formatMoney(cents: number, showSymbol = true): string {
  const yuan = centsToYuanInput(cents)
  const [integer, decimal] = yuan.replace('-', '').split('.')
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return `${cents < 0 ? '-' : ''}${showSymbol ? '¥' : ''}${grouped}.${decimal}`
}

export function formatTransactionMoney(cents: number, type: 'income' | 'expense'): string {
  return `${type === 'income' ? '+' : '-'}${formatMoney(cents)}`
}
