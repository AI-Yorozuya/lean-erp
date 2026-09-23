<script setup>
// ⚠ 原型（converge-intent 點畫面站產物）：假資料寫死、不碰 API；簽架構圖前可整檔重寫。
//    骨架照 ~/booking OrderDetailView（create 模式）：header 返回｜分隔線｜標題＋框線描述卡＋明細 3-table。
//    報價 domain 差異：品項「自由填」（不掛商品主檔——意圖收斂拍板：主幹先行）。
import { computed, nextTick, reactive, ref, onMounted, onUnmounted } from 'vue'
import { RouterLink, onBeforeRouteLeave } from 'vue-router'
import { ArrowLeft, Plus, X, Search } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import NumberInput from '@/components/NumberInput.vue'
import PillButton from '@/components/PillButton.vue'
import CustomerSelectDialog from '@/components/CustomerSelectDialog.vue'

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

// ── 錯誤貼在出問題的那一格旁邊，不是頁面頂端一行紅字 ──
// 頂端那種寫法在長表單裡等於沒說：使用者看得到「有錯」，看不到「錯在哪一格」。
const errors = reactive({ customer: '', items: '' })
const customerBtn = ref(null)
const addItemBtn = ref(null)
const focusEl = (r) => (r.value?.$el ?? r.value)?.focus?.()

async function send() {
  errors.customer = selected.value ? '' : '還沒選客戶'
  errors.items = form.items.length ? '' : '至少要有一行品項'
  // 送出後把游標移到第一個出錯的地方——不讓使用者自己在畫面上找紅字。
  if (errors.customer || errors.items) {
    await nextTick()
    focusEl(errors.customer ? customerBtn : addItemBtn)
    return
  }
  sent.value = true
}

// ── 打到一半離開要攔 ──
// 開新單這頁最容易把打了半天的單子弄丟：手滑點到側欄、按上一頁、關分頁都是。
const initial = JSON.stringify({ selected: null, form })
const dirty = computed(() => !sent.value && JSON.stringify({ selected: selected.value, form }) !== initial)

onBeforeRouteLeave(() => (dirty.value ? window.confirm('這張報價單還沒送出，離開就不見了。確定要離開嗎？') : true))

// 關分頁／重整走瀏覽器自己的攔截（訊息內容由瀏覽器決定，我們只負責說「有未存的東西」）。
function warnOnUnload(e) { if (dirty.value) e.preventDefault() }
onMounted(() => window.addEventListener('beforeunload', warnOnUnload))
onUnmounted(() => window.removeEventListener('beforeunload', warnOnUnload))
</script>

<template>
  <!-- 包成 form：在任何一格按 Enter 都送得出去（瀏覽器內建行為，不用自己綁 keyup）。
       注意——form 裡的 button 預設 type="submit"，所以不是送出的鈕都要寫 type="button"。 -->
  <form class="flex min-h-full flex-col" @submit.prevent="send">
    <div class="flex shrink-0 flex-wrap items-center gap-2">
      <!-- 回上一頁＝換頁，用連結；離開未存會被下面的 onBeforeRouteLeave 攔一次 -->
      <Button as-child variant="outline" size="sm" class="min-w-28 rounded-full">
        <RouterLink to="/quotations"><ArrowLeft class="size-4" /> 回上一頁</RouterLink>
      </Button>
      <div class="bg-border mx-1 h-6 w-px shrink-0"></div>
      <h1 class="text-lg leading-none font-semibold tracking-tight">開新單</h1>
      <div class="ml-10 flex items-center gap-2">
        <span class="text-muted-foreground text-sm">報價操作：</span>
        <PillButton type="submit" :disabled="sent">送出</PillButton>
      </div>
    </div>

    <div class="mt-5 flex min-h-0 flex-1 flex-col gap-4">
      <!-- 客戶卡（框線 descriptions）-->
      <div class="bg-card shrink-0 overflow-hidden rounded-lg border shadow-sm">
        <div class="border-b px-4 py-2.5 text-sm font-semibold">客戶</div>
        <dl class="grid grid-cols-1 text-sm sm:grid-cols-2">
          <div class="flex border-b">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">客戶名稱</dt>
            <dd class="flex-1">
              <button
                ref="customerBtn"
                type="button"
                class="hover:bg-muted/30 flex h-9 w-full cursor-pointer items-center justify-between px-3 text-sm transition-colors"
                :aria-invalid="!!errors.customer"
                :aria-describedby="errors.customer ? 'err-customer' : undefined"
                @click="showCustomerDialog = true"
              >
                <span :class="selected ? 'font-medium' : 'text-muted-foreground'">{{ selected ? selected.name : '搜尋 / 選擇客戶…' }}</span>
                <Search class="text-muted-foreground size-4" />
              </button>
              <p v-if="errors.customer" id="err-customer" class="text-destructive px-3 pb-1.5 text-xs">{{ errors.customer }}</p>
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
          <span class="text-sm font-semibold">
            明細
            <span v-if="errors.items" class="text-destructive ml-2 text-xs font-normal">{{ errors.items }}</span>
          </span>
          <Button ref="addItemBtn" type="button" variant="outline" size="sm" @click="addItem"><Plus class="size-4" /> 加一行</Button>
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
                  <Button type="button" variant="ghost" size="icon-sm" class="text-destructive" :aria-label="`刪除第 ${idx + 1} 行`" @click="removeItem(idx)"><X class="size-4" /></Button>
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
  </form>
</template>
