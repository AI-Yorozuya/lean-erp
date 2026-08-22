<script setup>
// 客戶挑選對話框（建單/報價時選客戶用）。參考 top-erp 的 OrderUserSelectDialog：
// 搜尋 + 伺服器端分頁的表格，點一列就選定——客戶多的時候，這比塞滿的下拉好用。
// 附「＋新客戶」快速建立：建完直接選定，不用離開這個框。
import { ref, computed, watch } from 'vue'
import { Search, Plus } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import Pagination from '@/components/Pagination.vue'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'

const props = defineProps({
  open: { type: Boolean, default: false },
  // 資料來源可注入：fetcher({page,pageSize,search}) → {items,count}；creator(payload) → item。
  // 原型期用假資料預設值；接真 API 時從外面傳 listCustomers/createCustomer 進來。
  fetcher: { type: Function, default: null },
  creator: { type: Function, default: null },
})

// ── 原型預設假資料（無 fetcher 時使用）──
const MOCK = [
  { id: 1, name: '王師傅工程行', phone: '0912-345-678' },
  { id: 2, name: '陳太太', phone: '0987-654-321' },
  { id: 3, name: '大直林先生', phone: '02-2533-1234' },
  { id: 4, name: '好室設計', phone: '02-8712-9922' },
  { id: 5, name: '永安水電', phone: '0933-110-220' },
  { id: 6, name: '幸福居家', phone: '0955-667-788' },
  { id: 7, name: '大同設備', phone: '03-322-4455' },
  { id: 8, name: '張先生', phone: '0910-222-333' },
  { id: 9, name: '巷口早餐店', phone: '02-2755-0101' },
  { id: 10, name: '立丰鐵工', phone: '0921-909-808' },
]
async function mockFetch({ page, pageSize, search }) {
  const all = MOCK.filter((m) => !search || m.name.includes(search) || m.phone.includes(search))
  return { items: all.slice((page - 1) * pageSize, page * pageSize), count: all.length }
}
async function mockCreate(payload) {
  const item = { id: Date.now(), ...payload }
  MOCK.unshift(item)
  return item
}
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
    const res = await (props.fetcher || mockFetch)({ page: page.value, pageSize, search: keyword.value })
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
  if (!newC.value.name || !newC.value.phone) {
    newErr.value = '姓名與電話必填'
    return
  }
  try {
    const created = await (props.creator || mockCreate)({ ...newC.value })
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
          <Input v-model="newC.phone" placeholder="電話" />
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
