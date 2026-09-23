<script setup>
// 商品列表（系統總覽・頁面 product_list）：搜尋、新增商品。一定顯示型號（rule_model_shown）。
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Plus, Search } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TableCell } from '@/components/ui/table'
import Pagination from '@/components/Pagination.vue'
import DataTable from '@/components/DataTable.vue'
import { listProducts, errorText } from '@/api'
import { fmtMoney } from '@/lib/format'
import { useListQuery } from '@/lib/useListQuery'

const columns = [
  { label: '型號', width: 'w-36' },
  { label: '品名' },
  { label: '單價', width: 'w-32', align: 'right' },
]

const L = useListQuery('products')
const rows = ref([])
const count = ref(0)
const loading = ref(true)
const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await listProducts({ search: L.keyword.value, page: L.page.value, pageSize: L.pageSize.value })
    rows.value = res.items
    count.value = res.count
  } catch (e) {
    rows.value = []
    loadError.value = errorText(e, '撈不到商品，確認後端有沒有開著，再重新整理一次')
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
    <h1 class="shrink-0 text-lg leading-none font-semibold tracking-tight">商品列表</h1>
    <div class="bg-card mt-5 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
      <div class="flex min-h-0 flex-1 flex-col p-5">
        <div class="mb-4 flex shrink-0 items-center justify-between gap-2">
          <div class="flex w-72 min-w-0">
            <Input v-model="L.searchInput.value" name="q" type="search" placeholder="搜型號或品名…" class="relative rounded-r-none focus-visible:z-10" @keyup.enter="L.search" />
            <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" aria-label="搜尋" @click="L.search"><Search class="size-4" /></Button>
          </div>
          <Button as-child class="shrink-0">
            <RouterLink to="/products/new"><Plus class="size-4" /> 新增商品</RouterLink>
          </Button>
        </div>
        <DataTable :items="rows" :columns="columns" :loading="loading">
          <template #row="{ item: r }">
            <TableCell class="tabular-nums"><RouterLink :to="`/products/${r.id}`" class="hover:text-primary hover:underline">{{ r.model }}</RouterLink></TableCell>
            <TableCell class="truncate font-medium" :title="r.name">{{ r.name }}</TableCell>
            <TableCell class="text-right tabular-nums">{{ fmtMoney(r.price) }}</TableCell>
          </template>
          <template #empty>
            <span v-if="loadError" class="text-destructive">{{ loadError }}</span>
            <template v-else>{{ L.keyword.value ? '找不到符合的商品' : '還沒有商品，按右上「新增商品」' }}</template>
          </template>
        </DataTable>
        <div class="mt-4 shrink-0">
          <Pagination :page="L.page.value" :total-pages="totalPages" :page-size="L.pageSize.value" @update:page="L.goPage" @update:page-size="L.setPageSize" />
        </div>
      </div>
    </div>
  </div>
</template>
