<script setup>
// ⚠ 原型（converge-intent 點畫面站產物）：假資料寫死、不碰 API；簽架構圖前可整檔重寫。
//    骨架整檔照 ~/booking OrderListView（訂單模組 UI 對齊 top/ns 版）搬，只換 domain 與假資料。
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { Plus, Search } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Pagination from '@/components/Pagination.vue'
import DataTable from '@/components/DataTable.vue'
import PillButton from '@/components/PillButton.vue'
import { TableCell } from '@/components/ui/table'

const route = useRoute()
const router = useRouter()

const columns = [
  { label: '單號', width: 'w-28' },
  { label: '客戶', width: 'w-36' },
  { label: '品項' },
  { label: '金額', width: 'w-28', align: 'right' },
  { label: '負責人', width: 'w-20' },
  { label: '掛了', width: 'w-20', align: 'center' },
  { label: '狀態', width: 'w-20', align: 'center' },
]

// 假資料（多到分頁是真的）
const names = ['王師傅工程行', '陳太太', '大直林先生', '好室設計', '張先生', '永安水電', '幸福居家', '大同設備', '巷口早餐店', '立丰鐵工']
const itemNames = ['浴室防水', '陽台磁磚', '廚房翻新', '鋁門窗更換', '隔間工程', '水電配線']
const rows = ref(Array.from({ length: 47 }, (_, i) => {
  const won = i % 5 === 3, lost = i % 7 === 5
  return {
    id: i + 1,
    quote_no: `Q08${String(22 - (i % 20)).padStart(2, '0')}-${String((i % 4) + 1).padStart(3, '0')}`,
    customer: names[i % names.length],
    item: itemNames[i % itemNames.length],
    amount: 8000 + (i * 7919) % 150000,
    owner: i % 3 === 0 ? '阿凱' : '你',
    days: won || lost ? null : (i * 3) % 14,
    state: won ? 'won' : lost ? 'lost' : 'open',
  }
}))

// 狀態文字式：在談＝粗體黑字（要行動），終態＝灰字
const stateLabel = { open: '在談', won: '成交', lost: '沒成' }
const stateClass = (s) => (s === 'open' ? 'font-medium text-foreground' : 'text-muted-foreground')

// tab：計數只掛「在談的」（要行動的才掛數字）
const statusTabs = [
  { key: 'all', label: '全部' },
  { key: 'open', label: '在談的' },
  { key: 'won', label: '成交' },
  { key: 'lost', label: '沒成' },
]
// ── 清單的狀態住在網址上 ──
// 重整不會跳回第一頁、網址貼給同事看到的是同一個畫面、從單子按上一頁回來條件還在。
// 預設值不寫進網址（?status=open&page=1 那種洗版沒必要），所以網址只長出真的改過的那幾個。
const DEFAULTS = { status: 'open', q: '', page: 1, size: 20 }
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
  // replace 不 push：換個 tab、改個關鍵字不該把上一頁鍵灌成一長串篩選歷史。
  router.replace({ query: q })
}
watch([activeStatus, keyword, page, pageSize], syncQuery)

// 反方向：按上一頁／下一頁、或直接貼一個網址進來，畫面要跟著網址走。
watch(
  () => route.query,
  (q) => {
    activeStatus.value = q.status || DEFAULTS.status
    keyword.value = q.q || DEFAULTS.q
    searchInput.value = keyword.value
    page.value = Number(q.page) || DEFAULTS.page
    pageSize.value = Number(q.size) || DEFAULTS.size
  },
)

const match = (r) => !keyword.value || r.customer.includes(keyword.value) || r.quote_no.includes(keyword.value) || r.item.includes(keyword.value)
const filtered = computed(() =>
  rows.value
    .filter((r) => (activeStatus.value === 'all' ? true : r.state === activeStatus.value) && match(r))
    .sort((a, b) => (b.days ?? -1) - (a.days ?? -1)),
)
const count = computed(() => filtered.value.length)
const openCount = computed(() => rows.value.filter((r) => r.state === 'open').length)
const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize.value)))
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
const fmtCount = (n) => (n > 999 ? '999+' : n)

// 網址上的頁碼可能超出範圍（換了條件、或別人貼來的舊網址）——拉回最後一頁，不要留一個空表格。
watch(totalPages, (n) => { if (page.value > n) page.value = n })

function selectStatus(key) { activeStatus.value = key; page.value = 1 }
function goPage(p) { page.value = Math.min(Math.max(1, p), totalPages.value) }
function setPageSize(n) { pageSize.value = n; page.value = 1 }
function search() { keyword.value = searchInput.value.trim(); page.value = 1 }
const settle = (r, state) => { r.state = state }

// ── 點進單子再回來，眼睛要落回原本那一行 ──
// 捲的是表身（DataTable 內部那層），不是 <main>——所以自己記。
// key 帶 fullPath：換了條件就是另一份清單，不該把舊位置套上去。
const tableRef = ref(null)
const scrollKey = () => `quotationList:${route.fullPath}`
onBeforeRouteLeave(() => {
  const y = tableRef.value?.bodyScroll?.scrollTop
  if (y) sessionStorage.setItem(scrollKey(), String(y))
})
onMounted(async () => {
  await nextTick()
  const y = Number(sessionStorage.getItem(scrollKey())) || 0
  if (y && tableRef.value?.bodyScroll) tableRef.value.bodyScroll.scrollTop = y
})
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg leading-none font-semibold tracking-tight">報價單列表</h1>

    <!-- 大卡片：頂部狀態 tab（全寬）＋內容（搜尋＋表格＋分頁）——照 OrderListView -->
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
            v-if="tab.key === 'open'"
            :class="[
              'inline-flex min-w-[1.25rem] items-center justify-center rounded-full px-1.5 py-0.5 text-xs tabular-nums',
              activeStatus === tab.key ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
            ]"
          >{{ fmtCount(openCount) }}</span>
        </button>
      </div>

      <div class="flex min-h-0 flex-1 flex-col p-5">
        <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
          <div class="flex w-72">
            <Input
              v-model="searchInput"
              placeholder="搜客戶、單號或品項（查舊價也在這）…"
              class="relative rounded-r-none focus-visible:z-10"
              @keyup.enter="search"
            />
            <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" aria-label="搜尋" @click="search">
              <Search class="size-4" />
            </Button>
          </div>
          <!-- 換頁的東西用連結不用按鈕：使用者才按得動 Cmd＋點擊、中鍵開新分頁 -->
          <Button as-child>
            <RouterLink to="/quotations/new"><Plus class="size-4" /> 開新單</RouterLink>
          </Button>
        </div>

        <DataTable ref="tableRef" :items="paged" :columns="columns" :actions-label="'結果'" actions-width="w-40">
          <template #row="{ item: r }">
            <!-- 單號：詳細頁還沒長出來，所以現在只是文字。等 QuotationDetailView 上線再換成
                 <RouterLink :to="`/quotations/${r.id}`" class="hover:text-primary hover:underline">。
                 在那之前不掛 hover 底線——看起來能點卻點不動，是最惹人生氣的一種假動作。 -->
            <TableCell class="tabular-nums">{{ r.quote_no }}</TableCell>
            <TableCell class="truncate font-medium">{{ r.customer }}</TableCell>
            <TableCell class="text-muted-foreground truncate">{{ r.item }}</TableCell>
            <TableCell class="text-right tabular-nums">{{ r.amount.toLocaleString() }}</TableCell>
            <TableCell>{{ r.owner }}</TableCell>
            <TableCell class="text-center tabular-nums" :class="r.days >= 4 ? 'text-destructive font-semibold' : ''">
              {{ r.days != null ? r.days + ' 天' : '—' }}
            </TableCell>
            <TableCell class="text-center"><span :class="stateClass(r.state)">{{ stateLabel[r.state] }}</span></TableCell>
          </template>
          <template #actions="{ item: r }">
            <template v-if="r.state === 'open'">
              <PillButton variant="outline" class="min-w-14" @click="settle(r, 'won')">成交</PillButton>
              <PillButton variant="ghost" class="text-muted-foreground min-w-14" @click="settle(r, 'lost')">沒成</PillButton>
            </template>
          </template>
          <template #empty>
            {{ keyword ? '找不到符合的報價單' : (activeStatus === 'all' ? '還沒有報價單——按右上「＋ 開新單」開第一張' : '此狀態目前沒有單') }}
          </template>
        </DataTable>

        <div class="mt-4 shrink-0">
          <Pagination :page="page" :total-pages="totalPages" :page-size="pageSize" @update:page="goPage" @update:page-size="setPageSize" />
        </div>
      </div>
    </div>
  </div>
</template>
