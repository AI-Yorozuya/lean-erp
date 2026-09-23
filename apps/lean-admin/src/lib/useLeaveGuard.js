// 改了沒存就離開要攔：換頁（含同一個元件內換網址）跟關分頁各攔一次。
// 回傳 leaveOpen／answer 給頁面接 ConfirmDialog；存檔成功要跳頁前呼叫 approve()。
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute } from 'vue-router'

export function useLeaveGuard(isDirty) {
  const route = useRoute()
  const approved = ref(false)
  const leaveOpen = ref(false)
  let resolver = null

  const dirty = () => !approved.value && isDirty()
  function guard() {
    if (!dirty()) return true
    leaveOpen.value = true
    return new Promise((resolve) => { resolver = resolve })
  }
  onBeforeRouteLeave(guard)
  onBeforeRouteUpdate(guard)
  watch(() => route.fullPath, () => { approved.value = false })

  const onUnload = (e) => { if (dirty()) e.preventDefault() }
  onMounted(() => window.addEventListener('beforeunload', onUnload))
  onUnmounted(() => window.removeEventListener('beforeunload', onUnload))

  return {
    leaveOpen,
    approve: () => { approved.value = true },
    answer: (ok) => { leaveOpen.value = false; resolver?.(ok); resolver = null },
  }
}
