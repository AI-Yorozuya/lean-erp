<script setup>
// ⚠ 原型（converge-intent 點畫面站產物）：假資料寫死、不碰 API；簽架構圖前可整檔重寫。
//    骨架照 ~/booking OrderDetailView（create 模式）：header 返回｜分隔線｜標題＋框線描述卡＋明細 3-table。
//    報價 domain 差異：品項「自由填」（不掛商品主檔——意圖收斂拍板：主幹先行）。
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Plus, X, Search } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import NumberInput from '@/components/NumberInput.vue'
import PillButton from '@/components/PillButton.vue'
import CustomerSelectDialog from '@/components/CustomerSelectDialog.vue'

const router = useRouter()
const money = (n) => Number(n).toLocaleString()

const selected = ref(null)
const showCustomerDialog = ref(false)

const form = reactive({
  valid_until: '',
  payment_terms: '完工後三日內付款',
  note: '',
  items: [
    { name: '浴室拆除', quantity: 1, unit_price: 8000 },
    { name: '防水工程', quantity: 6, unit_price: 2000 },
  ],
})
const itemSubtotal = (i) => (Number(i.quantity) || 0) * (Number(i.unit_price) || 0)
const total = computed(() => form.items.reduce((s, i) => s + itemSubtotal(i), 0))
const addItem = () => form.items.push({ name: '', quantity: 1, unit_price: 0 })
const removeItem = (idx) => form.items.splice(idx, 1)

const sent = ref(false)
const formError = ref('')
function send() {
  if (!selected.value) { formError.value = '請選擇客戶'; return }
  if (!form.items.length) { formError.value = '請至少填一行品項'; return }
  formError.value = ''
  sent.value = true
}
</script>

<template>
  <div class="flex min-h-full flex-col">
    <div class="flex shrink-0 flex-wrap items-center gap-2">
      <Button variant="outline" size="sm" class="min-w-28 rounded-full" @click="router.push('/quotations')"><ArrowLeft class="size-4" /> 回上一頁</Button>
      <div class="bg-border mx-1 h-6 w-px shrink-0"></div>
      <h1 class="text-lg leading-none font-semibold tracking-tight">開新單</h1>
      <div class="ml-10 flex items-center gap-2">
        <span class="text-muted-foreground text-sm">報價操作：</span>
        <PillButton :disabled="sent" @click="send">送出</PillButton>
      </div>
    </div>

    <p v-if="formError" class="text-destructive mt-4 shrink-0 text-sm">{{ formError }}</p>

    <div class="mt-5 flex min-h-0 flex-1 flex-col gap-4">
      <!-- 客戶卡（框線 descriptions）-->
      <div class="bg-card shrink-0 overflow-hidden rounded-lg border shadow-sm">
        <div class="border-b px-4 py-2.5 text-sm font-semibold">客戶</div>
        <dl class="grid grid-cols-1 text-sm sm:grid-cols-2">
          <div class="flex border-b">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">客戶名稱</dt>
            <dd class="flex-1">
              <button type="button" class="hover:bg-muted/30 flex h-9 w-full cursor-pointer items-center justify-between px-3 text-sm transition-colors" @click="showCustomerDialog = true">
                <span :class="selected ? 'font-medium' : 'text-muted-foreground'">{{ selected ? selected.name : '搜尋 / 選擇客戶…' }}</span>
                <Search class="text-muted-foreground size-4" />
              </button>
            </dd>
          </div>
          <div class="flex border-b sm:border-l">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">客戶電話</dt>
            <dd class="flex-1 px-3 py-2 tabular-nums">{{ selected?.phone || '—' }}</dd>
          </div>
          <div class="flex border-b">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">有效期限</dt>
            <dd class="flex-1"><input v-model="form.valid_until" placeholder="沒填代表不設限" class="focus:bg-muted/30 h-9 w-full bg-transparent px-3 text-sm outline-none" /></dd>
          </div>
          <div class="flex border-b sm:border-l">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">付款條件</dt>
            <dd class="flex-1"><input v-model="form.payment_terms" class="focus:bg-muted/30 h-9 w-full bg-transparent px-3 text-sm outline-none" /></dd>
          </div>
          <div class="flex sm:col-span-2">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">備註</dt>
            <dd class="flex-1"><input v-model="form.note" placeholder="自由文字" class="focus:bg-muted/30 h-9 w-full bg-transparent px-3 text-sm outline-none" /></dd>
          </div>
        </dl>
      </div>

      <!-- 明細卡（3-table；品名自由填）-->
      <div class="bg-card flex min-h-64 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
        <div class="flex shrink-0 items-center justify-between border-b px-4 py-2.5">
          <span class="text-sm font-semibold">明細</span>
          <Button variant="outline" size="sm" @click="addItem"><Plus class="size-4" /> 加一行</Button>
        </div>
        <div class="scroll-thin bg-card shrink-0 overflow-x-hidden overflow-y-scroll border-b">
          <Table class="table-fixed [&_th]:border-b-0">
            <colgroup><col /><col class="w-28" /><col class="w-28" /><col class="w-32" /><col class="w-12" /></colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>品名</TableHead>
                <TableHead class="text-right">單價</TableHead>
                <TableHead class="text-center">數量</TableHead>
                <TableHead class="text-right">小計</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
          </Table>
        </div>
        <div class="scroll-thin min-h-0 flex-1 overflow-y-scroll">
          <Table class="table-fixed [&_thead]:hidden">
            <colgroup><col /><col class="w-28" /><col class="w-28" /><col class="w-32" /><col class="w-12" /></colgroup>
            <TableBody>
              <TableRow v-for="(item, idx) in form.items" :key="idx">
                <TableCell><input v-model="item.name" placeholder="打品名" class="focus:bg-muted/30 h-9 w-full bg-transparent px-3 outline-none" /></TableCell>
                <TableCell><input v-model.number="item.unit_price" type="number" class="focus:bg-muted/30 h-9 w-full bg-transparent px-3 text-right outline-none" /></TableCell>
                <TableCell class="text-center"><NumberInput v-model="item.quantity" :min="1" /></TableCell>
                <TableCell class="text-right tabular-nums">{{ money(itemSubtotal(item)) }}</TableCell>
                <TableCell class="text-center">
                  <Button variant="ghost" size="icon-sm" class="text-destructive" @click="removeItem(idx)"><X class="size-4" /></Button>
                </TableCell>
              </TableRow>
              <TableRow v-if="!form.items.length" class="hover:bg-transparent">
                <TableCell colspan="5" class="text-muted-foreground py-10 text-center">還沒有品項——按右上「＋ 加一行」</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <div class="scroll-thin bg-card shrink-0 overflow-x-hidden overflow-y-scroll border-t">
          <Table class="table-fixed [&_td]:border-b-0">
            <colgroup><col /><col class="w-28" /><col class="w-28" /><col class="w-32" /><col class="w-12" /></colgroup>
            <TableBody>
              <TableRow class="hover:bg-transparent">
                <TableCell></TableCell>
                <TableCell></TableCell>
                <TableCell class="text-right font-semibold">總計</TableCell>
                <TableCell class="text-right font-semibold tabular-nums">{{ money(total) }}</TableCell>
                <TableCell></TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>

      <div v-if="sent" class="bg-card shrink-0 rounded-lg border-2 border-dashed p-6 text-center shadow-sm">
        <p class="font-semibold">📄 報價單 Q0822-001.pdf 已產生</p>
        <p class="text-muted-foreground mt-1 text-sm">自己用 LINE／email 傳給客人；單子已進「在談的」列表，之後修改都會留紀錄。</p>
      </div>
    </div>

    <!-- 挑客戶：正牌搜尋＋分頁表格 dialog（原型用內建假資料；接真 API 時傳 fetcher/creator）-->
    <CustomerSelectDialog :open="showCustomerDialog" @update:open="(v) => (showCustomerDialog = v)" @select="(c) => (selected = c)" />
  </div>
</template>
