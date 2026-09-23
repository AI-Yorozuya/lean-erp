<script setup>
// 客戶列表（系統總覽・頁面 customer_list）：搜尋、新增客戶。報價紀錄幾筆、最近一張從報價單反算。
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Plus, Search } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TableCell } from '@/components/ui/table'
import Pagination from '@/components/Pagination.vue'
import DataTable from '@/components/DataTable.vue'
import { listCustomers, errorText } from '@/api'
import { useListQuery } from '@/lib/useListQuery'

const columns = [
  { label: '客戶名稱' },
  { label: '聯絡人', width: 'w-32' },
  { label: '報價紀錄', width: 'w-24', align: 'right' },
  { label: '最近一張報價', width: 'w-44' },
]

const L = useListQuery('customers')
const rows = ref([])
const count = ref(0)
const loading = ref(true)
const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await listCustomers({ search: L.keyword.value, page: L.page.value, pageSize: L.pageSize.value })
    rows.value = res.items
    count.value = res.count
  } catch (e) {
    rows.value = []
    loadError.value = errorText(e, '撈不到客戶，確認後端有沒有開著，再重新整理一次')
  } finally {
    loading.value = false
  }
}
watch([L.keyword, L.page, L.pageSize], load)
onMounted(load)
const totalPages = computed(() => Math.max(1, Math.ceil(count.value / L.pageSize.value)))
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg leading-none font-semibold tracking-tight">客戶列表</h1>
    <div class="bg-card mt-5 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
      <div class="flex min-h-0 flex-1 flex-col p-5">
        <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
          <div class="flex w-72 min-w-0">
            <Input v-model="L.searchInput.value" name="q" type="search" placeholder="搜客戶名稱或聯絡人…" class="relative rounded-r-none focus-visible:z-10" @keyup.enter="L.search" />
            <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" aria-label="搜尋" @click="L.search"><Search class="size-4" /></Button>
          </div>
          <Button as-child class="shrink-0">
            <RouterLink to="/customers/new"><Plus class="size-4" /> 新增客戶</RouterLink>
          </Button>
        </div>
        <DataTable :items="rows" :columns="columns" :loading="loading">
          <template #row="{ item: r }">
            <TableCell class="truncate font-medium" :title="r.name"><RouterLink :to="`/customers/${r.id}`" class="hover:text-primary hover:underline">{{ r.name }}</RouterLink></TableCell>
            <TableCell class="truncate">{{ r.contact || '—' }}</TableCell>
            <TableCell class="text-right tabular-nums">{{ r.quote_count }} 筆</TableCell>
            <TableCell class="tabular-nums">
              <RouterLink v-if="r.last_quote_id" :to="`/quotations/${r.last_quote_id}`" class="text-muted-foreground hover:text-primary hover:underline">{{ r.last_quote_no }}</RouterLink>
              <span v-else class="text-muted-foreground">—</span>
            </TableCell>
          </template>
          <template #empty>
            <span v-if="loadError" class="text-destructive">{{ loadError }}</span>
            <template v-else>{{ L.keyword.value ? '找不到符合的客戶' : '還沒有客戶，按右上「新增客戶」' }}</template>
          </template>
        </DataTable>
        <div class="mt-4 shrink-0">
          <Pagination :page="L.page.value" :total-pages="totalPages" :page-size="L.pageSize.value" @update:page="L.goPage" @update:page-size="L.setPageSize" />
        </div>
      </div>
    </div>
  </div>
</template>
