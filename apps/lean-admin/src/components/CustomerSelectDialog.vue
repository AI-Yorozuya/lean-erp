<script setup>
// 選取客戶（系統總覽・互動元件 customer_picker，報價單詳細頁用）。
// 搜尋＋伺服器端分頁的表格，點一列就選定。客戶只能選取引用、不在報價單上打字（rule_customer_pick）。
import { computed, ref, watch } from 'vue'
import { Search } from '@lucide/vue'
import { listCustomers } from '@/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import Pagination from '@/components/Pagination.vue'

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
    const res = await listCustomers({ page: page.value, pageSize, search: keyword.value })
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
      <DialogHeader><DialogTitle>選取客戶</DialogTitle></DialogHeader>
      <div class="flex">
        <Input v-model="searchInput" type="search" placeholder="搜客戶名稱或聯絡人…" class="rounded-r-none focus-visible:z-10" @keyup.enter="search" />
        <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" aria-label="搜尋" @click="search"><Search class="size-4" /></Button>
      </div>
      <div class="max-h-[320px] min-h-[220px] overflow-auto rounded-md border">
        <Table class="table-fixed">
          <TableHeader>
            <TableRow>
              <TableHead>客戶名稱</TableHead>
              <TableHead class="w-28">聯絡人</TableHead>
              <TableHead class="w-40">最近報價</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="c in rows" :key="c.id" class="hover:bg-muted/60 cursor-pointer" @click="pick(c)">
              <TableCell class="truncate font-medium">{{ c.name }}</TableCell>
              <TableCell class="truncate">{{ c.contact || '—' }}</TableCell>
              <TableCell class="text-muted-foreground tabular-nums">{{ c.last_quote_no || '—' }}</TableCell>
            </TableRow>
            <TableRow v-if="!loading && !rows.length">
              <TableCell colspan="3" class="text-muted-foreground py-8 text-center">{{ keyword ? '找不到符合的客戶' : '還沒有客戶' }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
      <Pagination :page="page" :total-pages="totalPages" @update:page="goPage" />
    </DialogContent>
  </Dialog>
</template>
