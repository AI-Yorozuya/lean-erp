<script setup>
// ⚠ 原型（converge-intent 點畫面站產物）：假資料寫死、不碰 API；簽架構圖前可整檔重寫。
//    骨架整檔照 ~/booking OrderListView（訂單模組 UI 對齊 top/ns 版）搬，只換 domain 與假資料。
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Pagination from '@/components/Pagination.vue'
import DataTable from '@/components/DataTable.vue'
import PillButton from '@/components/PillButton.vue'
import { TableCell } from '@/components/ui/table'

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
const activeStatus = ref('open')
const searchInput = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)

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

function selectStatus(key) { activeStatus.value = key; page.value = 1 }
function goPage(p) { page.value = Math.min(Math.max(1, p), totalPages.value) }
function setPageSize(n) { pageSize.value = n; page.value = 1 }
function search() { keyword.value = searchInput.value.trim(); page.value = 1 }
const settle = (r, state) => { r.state = state }
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg leading-none font-semibold tracking-tight">報價單列表</h1>

    <!-- 大卡片：頂部狀態 tab（全寬）＋內容（搜尋＋表格＋分頁）——照 OrderListView -->
    <div class="bg-card mt-5 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
      <div class="flex shrink-0 border-b">
        <button
          v-for="tab in statusTabs"
          :key="tab.key"
          type="button"
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
            <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" @click="search">
              <Search class="size-4" />
            </Button>
          </div>
          <Button @click="router.push('/quotations/new')"><Plus class="size-4" /> 開新單</Button>
        </div>

        <DataTable :items="paged" :columns="columns" :actions-label="'結果'" actions-width="w-40">
          <template #row="{ item: r }">
            <TableCell class="tabular-nums">
              <button type="button" class="hover:text-primary hover:underline">{{ r.quote_no }}</button>
            </TableCell>
            <TableCell class="font-medium">{{ r.customer }}</TableCell>
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
