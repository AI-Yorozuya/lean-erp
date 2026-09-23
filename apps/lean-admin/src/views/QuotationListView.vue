<script setup>
// 報價單列表（系統總覽・頁面 quote_list）：狀態 tabs、搜尋、開新單。
// 骨架照 top/ns 清單頁：大卡裡放 tabs → 工具列（接合式搜尋＋開新單）→ DataTable → 分頁。
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Plus, Search } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TableCell } from '@/components/ui/table'
import Pagination from '@/components/Pagination.vue'
import DataTable from '@/components/DataTable.vue'
import { listQuotations, errorText } from '@/api'
import { fmtMoney, fmtDate } from '@/lib/format'
import { useListQuery } from '@/lib/useListQuery'

const columns = [
  { label: '單號', width: 'w-40' },
  { label: '客戶' },
  { label: '日期', width: 'w-28', align: 'center' },
  { label: '業務', width: 'w-24' },
  { label: '總額', width: 'w-32', align: 'right' },
  { label: '狀態', width: 'w-20', align: 'center' },
]
// tab 名稱＝系統總覽的狀態字。計數只掛要行動的：草稿（還沒匯出給客戶）。
const statusTabs = [
  { key: '', label: '全部' },
  { key: 'draft', label: '草稿', count: true },
  { key: 'sent', label: '已送出' },
]
const stateClass = (s) => (s === 'draft' ? 'font-medium text-foreground' : 'text-muted-foreground')

const L = useListQuery('quotations')
const rows = ref([])
const count = ref(0)
const counts = ref({})
const loading = ref(true)
const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await listQuotations({ status: L.status.value, search: L.keyword.value, page: L.page.value, pageSize: L.pageSize.value })
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
watch([L.status, L.keyword, L.page, L.pageSize], load)
onMounted(load)
const totalPages = computed(() => Math.max(1, Math.ceil(count.value / L.pageSize.value)))
const fmtCount = (n) => (n > 999 ? '999+' : n ?? 0)
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
          :aria-selected="L.status.value === tab.key"
          :class="[
            '-mb-px flex cursor-pointer items-center gap-1.5 border-b-2 px-4 py-3 text-sm whitespace-nowrap transition-colors',
            L.status.value === tab.key ? 'border-primary text-foreground font-medium' : 'text-muted-foreground hover:text-foreground border-transparent',
          ]"
          @click="L.selectStatus(tab.key)"
        >
          {{ tab.label }}
          <span
            v-if="tab.count"
            :class="[
              'inline-flex min-w-[1.25rem] items-center justify-center rounded-full px-1.5 py-0.5 text-xs tabular-nums',
              L.status.value === tab.key ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
            ]"
          >{{ fmtCount(counts[tab.key]) }}</span>
        </button>
      </div>

      <div class="flex min-h-0 flex-1 flex-col p-5">
        <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
          <div class="flex w-72 min-w-0">
            <Input v-model="L.searchInput.value" name="q" type="search" placeholder="搜單號、客戶、型號或品名…" class="relative rounded-r-none focus-visible:z-10" @keyup.enter="L.search" />
            <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" aria-label="搜尋" @click="L.search"><Search class="size-4" /></Button>
          </div>
          <Button as-child class="shrink-0">
            <RouterLink to="/quotations/new"><Plus class="size-4" /> 開新單</RouterLink>
          </Button>
        </div>

        <DataTable :items="rows" :columns="columns" :loading="loading">
          <template #row="{ item: r }">
            <TableCell class="tabular-nums"><RouterLink :to="`/quotations/${r.id}`" class="hover:text-primary hover:underline">{{ r.no }}</RouterLink></TableCell>
            <TableCell class="truncate font-medium" :title="r.customer_name">{{ r.customer_name }}</TableCell>
            <TableCell class="text-center tabular-nums">{{ fmtDate(r.date) }}</TableCell>
            <TableCell class="truncate">{{ r.sales_name }}</TableCell>
            <TableCell class="text-right tabular-nums">{{ fmtMoney(r.total) }}</TableCell>
            <TableCell class="text-center"><span :class="stateClass(r.status)">{{ r.status_display }}</span></TableCell>
          </template>
          <template #empty>
            <span v-if="loadError" class="text-destructive">{{ loadError }}</span>
            <template v-else>{{ L.keyword.value ? '找不到符合的報價單' : (L.status.value ? '這個狀態目前沒有單' : '還沒有報價單，按右上「開新單」開第一張') }}</template>
          </template>
        </DataTable>
        <div class="mt-4 shrink-0">
          <Pagination :page="L.page.value" :total-pages="totalPages" :page-size="L.pageSize.value" @update:page="L.goPage" @update:page-size="L.setPageSize" />
        </div>
      </div>
    </div>
  </div>
</template>
