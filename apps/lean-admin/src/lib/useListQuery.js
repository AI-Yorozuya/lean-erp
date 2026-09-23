// 清單頁共用：搜尋字、頁碼、每頁筆數（有 tab 的再加狀態）住在網址上。
// 重整、貼給同事、上一頁回來，看到的都是同一個畫面。換條件用 replace，不把上一頁灌成一串篩選。
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useListQuery(routeName, defaults = {}) {
  const D = { status: '', q: '', page: 1, size: 20, ...defaults }
  const route = useRoute()
  const router = useRouter()
  const status = ref(route.query.status || D.status)
  const searchInput = ref(route.query.q || D.q)
  const keyword = ref(route.query.q || D.q)
  const page = ref(Number(route.query.page) || D.page)
  const pageSize = ref(Number(route.query.size) || D.size)

  watch([status, keyword, page, pageSize], () => {
    const q = {}
    if (status.value !== D.status) q.status = status.value
    if (keyword.value) q.q = keyword.value
    if (page.value !== D.page) q.page = String(page.value)
    if (pageSize.value !== D.size) q.size = String(pageSize.value)
    router.replace({ query: q })
  })
  watch(() => route.query, (q) => {
    if (route.name !== routeName) return
    status.value = q.status || D.status
    keyword.value = q.q || D.q
    searchInput.value = keyword.value
    page.value = Number(q.page) || D.page
    pageSize.value = Number(q.size) || D.size
  })

  return {
    status, searchInput, keyword, page, pageSize,
    search: () => { keyword.value = searchInput.value.trim(); page.value = 1 },
    selectStatus: (s) => { status.value = s; page.value = 1 },
    goPage: (p) => { page.value = p },
    setPageSize: (n) => { pageSize.value = n; page.value = 1 },
  }
}
