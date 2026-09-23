<script setup>
// 訂單列表：依狀態看（架構圖〈頁面〉）。骨架跟報價單列表同一套。
// 訂單只能從成交的報價單轉出來，所以這頁沒有「開新單」。
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { Search } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TableCell } from '@/components/ui/table'
import Pagination from '@/components/Pagination.vue'
import DataTable from '@/components/DataTable.vue'
import { listOrders, errorText } from '@/api'
import { fmtMoney, fmtDate, fmtDay } from '@/lib/format'

const route = useRoute()
const router = useRouter()

const columns = [
  { label: '訂單號', width: 'w-36' },
  { label: '客戶' },
  { label: '來源報價單', width: 'w-36' },
  { label: '總額', width: 'w-28', align: 'right' },
  { label: '轉單日', width: 'w-28', align: 'center' },
  { label: '預計交付', width: 'w-28', align: 'center' },
  { label: '狀態', width: 'w-20', align: 'center' },
]

// tab 名稱＝架構圖的狀態字。計數只掛要行動的：待處理、處理中。
const statusTabs = [
  { key: 'all', label: '全部' },
  { key: 'pending', label: '待處理', count: true },
  { key: 'processing', label: '處理中', count: true },
  { key: 'done', label: '完成' },
  { key: 'void', label: '已作廢' },
]
const stateClass = (s) => (s === 'pending' || s === 'processing' ? 'font-medium text-foreground' : 'text-muted-foreground')

// ── 清單的狀態住在網址上：重整、貼給同事、上一頁回來，看到的都是同一個畫面 ──
const DEFAULTS = { status: 'all', q: '', page: 1, size: 20 }
const activeStatus = ref(route.query.status || DEFAULTS.status)
const searchInput = ref(route.query.q || DEFAULTS.q)
const keyword = ref(route.query.q || DEFAULTS.q)
const page = ref(Number(route.query.page) || DEFAULTS.page)
const pageSize = ref(Number(route.query.size) || DEFAULTS.size)

function syncQuery() {
  const q = {}
  if (activeStatus.value !== DEFAULTS.status) q.status = activeStatus.value
  if (keyword.value) q.q = keyword.value
  if (page.value !== DEFAULTS.page) q.page = String(page.value)
  if (pageSize.value !== DEFAULTS.size) q.size = String(pageSize.value)
  router.replace({ query: q })
}
watch(
  () => route.query,
  (q) => {
    if (route.name !== 'orders') return
    activeStatus.value = q.status || DEFAULTS.status
    keyword.value = q.q || DEFAULTS.q
    searchInput.value = keyword.value
    page.value = Number(q.page) || DEFAULTS.page
    pageSize.value = Number(q.size) || DEFAULTS.size
  },
)

// ── 撈資料（換 tab／搜尋／換頁都重撈）──
const rows = ref([])
const count = ref(0)
const counts = ref({})
const loading = ref(true)
const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await listOrders({
      status: activeStatus.value === 'all' ? '' : activeStatus.value,
      search: keyword.value,
      page: page.value,
      pageSize: pageSize.value,
    })
    rows.value = res.rows
    count.value = res.count
    counts.value = res.counts
  } catch (e) {
    rows.value = []
    loadError.value = errorText(e, '撈不到訂單，確認後端有沒有開著，再重新整理一次')
  } finally {
    loading.value = false
  }
}
watch([activeStatus, keyword, page, pageSize], () => {
  syncQuery()
  load()
})

const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize.value)))
watch(totalPages, (n) => { if (page.value > n) page.value = n })
const fmtCount = (n) => (n > 999 ? '999+' : n ?? 0)

function selectStatus(key) { activeStatus.value = key; page.value = 1 }
function goPage(p) { page.value = Math.min(Math.max(1, p), totalPages.value) }
function setPageSize(n) { pageSize.value = n; page.value = 1 }
function search() { keyword.value = searchInput.value.trim(); page.value = 1 }

// ── 點進單子再回來，眼睛要落回原本那一行 ──
const tableRef = ref(null)
const scrollKey = () => `orderList:${route.fullPath}`
onBeforeRouteLeave(() => {
  const y = tableRef.value?.bodyScroll?.scrollTop
  if (y) sessionStorage.setItem(scrollKey(), String(y))
})
onMounted(async () => {
  await load()
  await nextTick()
  const y = Number(sessionStorage.getItem(scrollKey())) || 0
  if (y && tableRef.value?.bodyScroll) tableRef.value.bodyScroll.scrollTop = y
})
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg leading-none font-semibold tracking-tight">訂單列表</h1>

    <div class="bg-card mt-5 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
      <div class="flex shrink-0 border-b" role="tablist" aria-label="訂單狀態">
        <button
          v-for="tab in statusTabs"
          :key="tab.key"
          type="button"
          role="tab"
          :aria-selected="activeStatus === tab.key"
          :class="[
            '-mb-px flex cursor-pointer items-center gap-1.5 border-b-2 px-4 py-3 text-sm whitespace-nowrap transition-colors',
            activeStatus === tab.key ? 'border-primary text-foreground font-medium' : 'text-muted-foreground hover:text-foreground border-transparent',
          ]"
          @click="selectStatus(tab.key)"
        >
          {{ tab.label }}
          <span
            v-if="tab.count"
            :class="[
              'inline-flex min-w-[1.25rem] items-center justify-center rounded-full px-1.5 py-0.5 text-xs tabular-nums',
              activeStatus === tab.key ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
            ]"
          >{{ fmtCount(counts[tab.key]) }}</span>
        </button>
      </div>

      <div class="flex min-h-0 flex-1 flex-col p-5">
        <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
          <div class="flex w-72 min-w-0">
            <Input
              v-model="searchInput"
              name="q"
              type="search"
              placeholder="搜客戶、訂單號或報價單號…"
              class="relative rounded-r-none focus-visible:z-10"
              @keyup.enter="search"
            />
            <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" aria-label="搜尋" @click="search">
              <Search class="size-4" />
            </Button>
          </div>
        </div>

        <DataTable ref="tableRef" :items="rows" :columns="columns" :loading="loading">
          <template #row="{ item: r }">
            <TableCell class="tabular-nums">
              <RouterLink :to="`/orders/${r.id}`" class="hover:text-primary hover:underline">{{ r.no }}</RouterLink>
            </TableCell>
            <TableCell class="truncate font-medium" :title="r.customer_name">{{ r.customer_name }}</TableCell>
            <TableCell class="tabular-nums">
              <RouterLink :to="`/quotations/${r.quotation_id}`" class="text-muted-foreground hover:text-primary hover:underline">{{ r.quotation_no }}</RouterLink>
            </TableCell>
            <TableCell class="text-right tabular-nums">{{ fmtMoney(r.total) }}</TableCell>
            <TableCell class="text-center tabular-nums">{{ fmtDay(r.created_at) }}</TableCell>
            <TableCell class="text-center tabular-nums">{{ fmtDate(r.expected_delivery) }}</TableCell>
            <TableCell class="text-center"><span :class="stateClass(r.status)">{{ r.status_display }}</span></TableCell>
          </template>
          <template #empty>
            <span v-if="loadError" class="text-destructive">{{ loadError }}</span>
            <template v-else>
              {{ keyword ? '找不到符合的訂單' : (activeStatus === 'all' ? '還沒有訂單，報價單成交後按「轉成訂單」' : '這個狀態目前沒有訂單') }}
            </template>
          </template>
        </DataTable>

        <div class="mt-4 shrink-0">
          <Pagination :page="page" :total-pages="totalPages" :page-size="pageSize" @update:page="goPage" @update:page-size="setPageSize" />
        </div>
      </div>
    </div>
  </div>
</template>
