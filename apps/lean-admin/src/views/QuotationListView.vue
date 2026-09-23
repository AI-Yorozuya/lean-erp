<script setup>
// 報價單列表（intents/報價單列表.md）：狀態 tabs、盯單排序、查舊價。
// 骨架照 top/ns 清單頁：大卡裡放 tabs → 工具列（接合式搜尋＋開新單）→ DataTable → 分頁。
// 排序由後端決定（已送出＝掛越久排越上；其他＝送出日新到舊），前端不再排一次。
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { Plus, Search } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TableCell } from '@/components/ui/table'
import Pagination from '@/components/Pagination.vue'
import DataTable from '@/components/DataTable.vue'
import { listQuotations, errorText } from '@/api'
import { fmtMoney, fmtDate, daysLeftText } from '@/lib/format'

const route = useRoute()
const router = useRouter()

const columns = [
  { label: '單號', width: 'w-36' },
  { label: '客戶' },
  { label: '總額', width: 'w-28', align: 'right' },
  { label: '負責人', width: 'w-24' },
  { label: '送出日', width: 'w-28', align: 'center' },
  { label: '掛了', width: 'w-20', align: 'center' },
  { label: '有效期限', width: 'w-24', align: 'center' },
  { label: '狀態', width: 'w-20', align: 'center' },
]

// tab 名稱＝架構圖的狀態字，不另造詞。計數只掛要行動的：草擬（還沒送）、已送出（要追）。
const statusTabs = [
  { key: 'all', label: '全部' },
  { key: 'draft', label: '草擬', count: true },
  { key: 'sent', label: '已送出', count: true },
  { key: 'won', label: '已成交' },
  { key: 'lost', label: '沒成' },
]
const stateClass = (s) => (s === 'draft' || s === 'sent' ? 'font-medium text-foreground' : 'text-muted-foreground')

// ── 清單的狀態住在網址上：重整、貼給同事、上一頁回來，看到的都是同一個畫面 ──
// 每天打開先看「已送出」：該追的一眼看見（意圖：盯單）。
const DEFAULTS = { status: 'sent', q: '', page: 1, size: 20 }
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
    if (route.name !== 'quotations') return
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
    const res = await listQuotations({
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
    loadError.value = errorText(e, '撈不到報價單，確認後端有沒有開著，再重新整理一次')
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

// 已送出的單掛了幾天（從送出日算到今天）
const today = new Date(new Date().toDateString())
const hangingDays = (r) =>
  r.status === 'sent' && r.sent_on ? Math.round((today - new Date(`${r.sent_on}T00:00:00`)) / 86400000) : null

// ── 點進單子再回來，眼睛要落回原本那一行 ──
const tableRef = ref(null)
const scrollKey = () => `quotationList:${route.fullPath}`
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
    <h1 class="shrink-0 text-lg leading-none font-semibold tracking-tight">報價單列表</h1>

    <div class="bg-card mt-5 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
      <div class="flex shrink-0 border-b" role="tablist" aria-label="報價單狀態">
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
              placeholder="搜客戶或品名（查舊價）…"
              class="relative rounded-r-none focus-visible:z-10"
              @keyup.enter="search"
            />
            <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" aria-label="搜尋" @click="search">
              <Search class="size-4" />
            </Button>
          </div>
          <Button as-child class="shrink-0">
            <RouterLink to="/quotations/new"><Plus class="size-4" /> 開新單</RouterLink>
          </Button>
        </div>

        <DataTable ref="tableRef" :items="rows" :columns="columns" :loading="loading">
          <template #row="{ item: r }">
            <TableCell class="tabular-nums">
              <RouterLink :to="`/quotations/${r.id}`" class="hover:text-primary hover:underline">{{ r.no }}</RouterLink>
            </TableCell>
            <TableCell class="truncate font-medium" :title="r.customer_name">{{ r.customer_name }}</TableCell>
            <TableCell class="text-right tabular-nums">{{ fmtMoney(r.total) }}</TableCell>
            <TableCell class="truncate">{{ r.owner_name }}</TableCell>
            <TableCell class="text-center tabular-nums">{{ fmtDate(r.sent_on) }}</TableCell>
            <TableCell class="text-center tabular-nums">{{ hangingDays(r) != null ? `${hangingDays(r)} 天` : '—' }}</TableCell>
            <TableCell class="text-center" :class="r.is_expired && r.status === 'sent' ? 'text-destructive font-medium' : 'text-muted-foreground'">
              {{ daysLeftText(r.days_left) }}
            </TableCell>
            <TableCell class="text-center"><span :class="stateClass(r.status)">{{ r.status_display }}</span></TableCell>
          </template>
          <template #empty>
            <span v-if="loadError" class="text-destructive">{{ loadError }}</span>
            <template v-else>
              {{ keyword ? '找不到符合的報價單' : (activeStatus === 'all' ? '還沒有報價單，按右上「開新單」開第一張' : '這個狀態目前沒有單') }}
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
