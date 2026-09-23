<script setup>
// 選取商品（系統總覽・互動元件 product_picker，報價單詳細頁「新增品項」用）。
// 一定顯示型號：同名商品靠型號分（rule_model_shown）。單價照價目表帶入，報價單上不能改。
import { computed, ref, watch } from 'vue'
import { Search } from '@lucide/vue'
import { listProducts } from '@/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import Pagination from '@/components/Pagination.vue'
import { fmtMoney } from '@/lib/format'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['update:open', 'select'])

const rows = ref([])
const count = ref(0)
const loading = ref(false)
const searchInput = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = 8
const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize)))

async function load() {
  loading.value = true
  try {
    const res = await listProducts({ page: page.value, pageSize, search: keyword.value })
    rows.value = res.items
    count.value = res.count
  } finally {
    loading.value = false
  }
}
watch(() => props.open, (v) => {
  if (!v) return
  searchInput.value = ''
  keyword.value = ''
  page.value = 1
  load()
})
function search() { keyword.value = searchInput.value.trim(); page.value = 1; load() }
function goPage(p) { page.value = p; load() }
function pick(row) { emit('select', row); emit('update:open', false) }
</script>

<template>
  <Dialog :open="open" @update:open="(v) => emit('update:open', v)">
    <DialogContent class="overscroll-contain sm:max-w-2xl">
      <DialogHeader><DialogTitle>選取商品</DialogTitle></DialogHeader>
      <div class="flex">
        <Input v-model="searchInput" type="search" placeholder="搜型號或品名…" class="rounded-r-none focus-visible:z-10" @keyup.enter="search" />
        <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" aria-label="搜尋" @click="search"><Search class="size-4" /></Button>
      </div>
      <div class="max-h-[320px] min-h-[220px] overflow-auto rounded-md border">
        <Table class="table-fixed">
          <TableHeader>
            <TableRow>
              <TableHead class="w-32">型號</TableHead>
              <TableHead>品名</TableHead>
              <TableHead class="w-28 text-right">單價</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="p in rows" :key="p.id" class="hover:bg-muted/60 cursor-pointer" @click="pick(p)">
              <TableCell class="tabular-nums">{{ p.model }}</TableCell>
              <TableCell class="truncate font-medium">{{ p.name }}</TableCell>
              <TableCell class="text-right tabular-nums">{{ fmtMoney(p.price) }}</TableCell>
            </TableRow>
            <TableRow v-if="!loading && !rows.length">
              <TableCell colspan="3" class="text-muted-foreground py-8 text-center">{{ keyword ? '找不到符合的商品' : '還沒有商品' }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
      <Pagination :page="page" :total-pages="totalPages" @update:page="goPage" />
    </DialogContent>
  </Dialog>
</template>
