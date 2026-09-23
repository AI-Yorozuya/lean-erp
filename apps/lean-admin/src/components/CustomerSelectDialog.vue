<script setup>
// 客戶挑選對話框（建單/報價時選客戶用）。參考 top-erp 的 OrderUserSelectDialog：
// 搜尋 + 伺服器端分頁的表格，點一列就選定——客戶多的時候，這比塞滿的下拉好用。
// 附「＋新客戶」快速建立：建完直接選定，不用離開這個框。
import { ref, computed, watch } from 'vue'
import { Search, Plus } from '@lucide/vue'
import { listCustomers, createCustomer } from '@/api'

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
  // 資料來源可注入：fetcher({page,pageSize,search}) → {items,count}；creator(payload) → item。預設接真 API。
  fetcher: { type: Function, default: listCustomers },
  creator: { type: Function, default: createCustomer },
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

async function load() {
  loading.value = true
  try {
    const res = await props.fetcher({ page: page.value, pageSize, search: keyword.value })
    rows.value = res.items
    count.value = res.count
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// 每次打開重置＋載第一頁。
watch(() => props.open, (v) => {
  if (v) {
    searchInput.value = ''
    keyword.value = ''
    page.value = 1
    showNew.value = false
    newC.value = { name: '', phone: '' }
    newErr.value = ''
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

// ── 新客戶快速建立 ──
const showNew = ref(false)
const newC = ref({ name: '', phone: '' })
const newErr = ref('')
async function createNew() {
  newErr.value = ''
  if (!newC.value.name.trim() || !newC.value.phone.trim()) {
    newErr.value = '姓名與電話必填'
    return
  }
  try {
    const created = await props.creator({ name: newC.value.name.trim(), phone: newC.value.phone.trim() })
    pick(created)  // 建完直接選定並關框
  } catch (e) {
    newErr.value = e.response?.data?.detail || '建立失敗'
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="(v) => emit('update:open', v)">
    <DialogContent class="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle>選擇客戶</DialogTitle>
      </DialogHeader>

      <!-- 搜尋列 + 新客戶 -->
      <div class="flex items-center gap-2">
        <div class="flex flex-1">
          <Input
            v-model="searchInput"
            placeholder="搜尋客戶姓名或電話…"
            class="rounded-r-none focus-visible:z-10"
            @keyup.enter="search"
          />
          <Button variant="outline" size="icon" class="shrink-0 rounded-l-none border-l-0" title="搜尋" :disabled="!searchInput.trim()" @click="search">
            <Search class="size-4" />
          </Button>
        </div>
        <Button variant="outline" @click="showNew = !showNew"><Plus class="size-4" /> 新客戶</Button>
      </div>

      <!-- 新客戶快速建立 -->
      <div v-if="showNew" class="bg-muted flex flex-col gap-2 rounded-md p-3">
        <div class="flex gap-2">
          <Input v-model="newC.name" placeholder="姓名" />
          <Input v-model="newC.phone" type="tel" autocomplete="tel" placeholder="電話" @keyup.enter="createNew" />
          <Button class="shrink-0" @click="createNew">建立並選定</Button>
        </div>
        <p v-if="newErr" class="text-destructive text-sm">{{ newErr }}</p>
      </div>

      <!-- 客戶表格（點一列即選定）-->
      <div class="max-h-[320px] min-h-[220px] overflow-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>姓名</TableHead>
              <TableHead class="w-32">電話</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="c in rows"
              :key="c.id"
              class="hover:bg-muted/60 cursor-pointer"
              @click="pick(c)"
            >
              <TableCell class="font-medium">{{ c.name }}</TableCell>
              <TableCell class="tabular-nums">{{ c.phone || '—' }}</TableCell>
            </TableRow>
            <TableRow v-if="!loading && !rows.length">
              <TableCell colspan="2" class="text-muted-foreground py-8 text-center">
                {{ keyword ? '找不到符合的客戶——按「＋新客戶」建一位' : '還沒有客戶' }}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      <Pagination :page="page" :total-pages="totalPages" @update:page="goPage" />
    </DialogContent>
  </Dialog>
</template>
