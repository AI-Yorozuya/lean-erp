<script setup>
// 商品挑選對話框（建單/報價加品項時用）。跟 CustomerSelectDialog 同形：
// 搜尋 + 伺服器端分頁的表格，點一列就把該商品加進明細——商品多也不怕，比塞滿的下拉好用。
import { ref, computed, watch } from 'vue'
import { Search } from '@lucide/vue'
import { listProducts } from '@/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import Pagination from '@/components/Pagination.vue'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open', 'select'])

const rows = ref([])
const count = ref(0)
const loading = ref(false)
const searchInput = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = 8
const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize)))

const money = (n) => Number(n).toLocaleString()

async function load() {
  loading.value = true
  try {
    const res = await listProducts({ page: page.value, pageSize, search: keyword.value })
    rows.value = res.items
    count.value = res.count
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

watch(() => props.open, (v) => {
  if (v) {
    searchInput.value = ''
    keyword.value = ''
    page.value = 1
    load()
  }
})

function search() {
  keyword.value = searchInput.value.trim()
  page.value = 1
  load()
}
function goPage(p) {
  page.value = p
  load()
}
function pick(row) {
  emit('select', row)
  emit('update:open', false)
}
</script>

<template>
  <Dialog :open="open" @update:open="(v) => emit('update:open', v)">
    <DialogContent class="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle>選擇商品</DialogTitle>
      </DialogHeader>

      <div class="flex items-center gap-2">
        <div class="flex flex-1">
          <Input
            v-model="searchInput"
            placeholder="搜尋品名…"
            class="rounded-r-none focus-visible:z-10"
            @keyup.enter="search"
          />
          <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" :disabled="!searchInput.trim()" @click="search">
            <Search class="size-4" />
          </Button>
        </div>
      </div>

      <div class="max-h-[320px] min-h-[220px] overflow-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>品名</TableHead>
              <TableHead class="w-32 text-right">預設單價</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="p in rows"
              :key="p.id"
              class="hover:bg-muted/60 cursor-pointer"
              @click="pick(p)"
            >
              <TableCell class="truncate font-medium">{{ p.name }}</TableCell>
              <TableCell class="text-right tabular-nums">{{ money(p.default_price) }}</TableCell>
            </TableRow>
            <TableRow v-if="!loading && !rows.length">
              <TableCell colspan="2" class="text-muted-foreground py-8 text-center">
                {{ keyword ? '找不到符合的商品' : '還沒有商品' }}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      <Pagination :page="page" :total-pages="totalPages" @update:page="goPage" />
    </DialogContent>
  </Dialog>
</template>
