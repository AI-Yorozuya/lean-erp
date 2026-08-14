// 極簡 toast：頁面級錯誤/提示浮出畫面右上，幾秒後自己走。
// 為什麼要有它：錯誤塞在頁面頂端一行字，捲下去操作時根本看不到（ui-待修清單「全站」）。
// dialog 內的錯誤仍然就地顯示（人就盯著 dialog，不用飛出來）。
import { ref } from 'vue'

export const toasts = ref([])
let seq = 0

export function toast(message, kind = 'error', timeout = 4500) {
  const id = ++seq
  toasts.value.push({ id, message, kind })
  setTimeout(() => dismiss(id), timeout)
}

export function dismiss(id) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}
