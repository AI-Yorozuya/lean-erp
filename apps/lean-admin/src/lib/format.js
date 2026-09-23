// 日期與數字一律交給 Intl，不自己拼字串。
const money = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 })
const qtyFmt = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 2 })
const dateFmt = new Intl.DateTimeFormat('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' })
const dateTimeFmt = new Intl.DateTimeFormat('zh-TW', {
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
})

export const fmtMoney = (n) => money.format(Number(n) || 0)
export const fmtQty = (n) => qtyFmt.format(Number(n) || 0)
// 後端給的是 'YYYY-MM-DD'：當本地日期解，避免時區把日子往前推一天
export const fmtDate = (s) => (s ? dateFmt.format(new Date(`${s}T00:00:00`)) : '—')
export const fmtDateTime = (s) => (s ? dateTimeFmt.format(new Date(s)) : '—')

// 有效期限剩幾天：過期、今天到期、剩 N 天、不設限
export function daysLeftText(days) {
  if (days == null) return '不設限'
  if (days < 0) return '已過期'
  if (days === 0) return '今天到期'
  return `剩 ${days} 天`
}
// 後端給的是完整時間（ISO）但只要看哪一天
export const fmtDay = (iso) => (iso ? dateFmt.format(new Date(iso)) : '—')
