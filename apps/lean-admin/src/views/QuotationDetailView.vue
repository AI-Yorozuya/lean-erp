<script setup>
// 報價單詳細頁：一個檔管開新單／檢視／編輯三個模式（照 ns/top：同一個骨架，只換可編輯的格子）。
// 規格：建立報價單、送出與收回、點結果、轉成訂單（intents/ 同名 md）。
// 這頁能按哪些鍵，照後端給的 actions 出——狀態不對的動作不出現，前端不自己猜。
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { RouterLink, onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, FileDown, Plus, Search, X } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import NumberInput from '@/components/NumberInput.vue'
import PillButton from '@/components/PillButton.vue'
import DatePicker from '@/components/DatePicker.vue'
import LoadingState from '@/components/LoadingState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CustomerSelectDialog from '@/components/CustomerSelectDialog.vue'
import ProductSelectDialog from '@/components/ProductSelectDialog.vue'
import {
  getQuotation, createQuotation, updateQuotation, quotationAction, quotationPdfUrl, convertToOrder, errorText,
} from '@/api'
import { useSession } from '@/session'
import { toast } from '@/lib/toast'
import { fmtMoney, fmtDate, fmtDateTime, daysLeftText } from '@/lib/format'

const route = useRoute()
const router = useRouter()
const { user } = useSession()

const mode = computed(() => (route.name === 'quotation-new' ? 'create' : route.name === 'quotation-edit' ? 'edit' : 'view'))
const editing = computed(() => mode.value !== 'view')

// ── 資料 ──
const q = ref(null)
const loading = ref(false)
const loadError = ref('')

const emptyForm = () => ({ customer: null, valid_until: '', payment_terms: '完工後三日內付款', note: '', items: [] })
const form = reactive(emptyForm())
let snapshot = ''
const takeSnapshot = () => { snapshot = JSON.stringify(form) }

function fillForm(src) {
  Object.assign(form, src
    ? {
        customer: { id: src.customer_id, name: src.customer_name, phone: src.customer_phone },
        valid_until: src.valid_until || '',
        payment_terms: src.payment_terms,
        note: src.note,
        items: src.items.map((i) => ({ name: i.name, qty: Number(i.qty), unit_price: i.unit_price, product_id: i.product_id })),
      }
    : emptyForm())
  takeSnapshot()
}

const QUOTATION_ROUTES = ['quotation-new', 'quotation-detail', 'quotation-edit']

async function load() {
  if (!QUOTATION_ROUTES.includes(route.name)) return   // 正在離開這頁（例如轉單後跳去訂單）
  if (mode.value === 'create') {
    q.value = null
    fillForm(null)
    return
  }
  const id = Number(route.params.id)
  if (q.value?.id === id) {       // 同一張單在檢視／編輯之間切換：不重撈、不閃
    if (editing.value) fillForm(q.value)
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    q.value = await getQuotation(id)
    if (editing.value) fillForm(q.value)
  } catch (e) {
    loadError.value = e.response?.status === 404 ? '找不到這張報價單' : errorText(e, '撈不到這張報價單，稍後再試')
  } finally {
    loading.value = false
  }
}
watch(() => [route.name, route.params.id], load)
onMounted(load)

// ── 明細（編輯中）──
const lineSubtotal = (i) => (Number(i.qty) || 0) * (Number(i.unit_price) || 0)
const shownItems = computed(() => (editing.value ? form.items : q.value?.items ?? []))
const total = computed(() => (editing.value ? form.items.reduce((s, i) => s + lineSubtotal(i), 0) : Number(q.value?.total ?? 0)))
const showCustomerDialog = ref(false)
const showProductDialog = ref(false)
function addProduct(p) {
  form.items.push({ name: p.name, qty: 1, unit_price: p.default_price, product_id: p.id })
  errors.items = ''
}
function addFreeLine() {
  form.items.push({ name: '', qty: 1, unit_price: 0, product_id: null })
  errors.items = ''
  nextTick(() => [...document.querySelectorAll('[data-line-name]')].at(-1)?.focus())
}
const removeLine = (idx) => form.items.splice(idx, 1)

// ── 存檔（開新單＝存草稿；編輯＝儲存）──
const errors = reactive({ customer: '', items: '' })
const customerBtn = ref(null)
const saving = ref(false)
const leaveApproved = ref(false)   // 存檔成功後要跳頁：放行（要是 ref，dirty 才會重算）

function validate() {
  errors.customer = form.customer ? '' : '還沒選客戶'
  errors.items = !form.items.length ? '至少要有一行品項' : form.items.some((i) => !i.name.trim()) ? '有品項沒填品名' : ''
  return !errors.customer && !errors.items
}

async function save() {
  if (!validate()) {
    await nextTick()
    if (errors.customer) customerBtn.value?.focus()
    return
  }
  const payload = {
    valid_until: form.valid_until || null,
    payment_terms: form.payment_terms.trim(),
    note: form.note.trim(),
    items: form.items.map((i) => ({ name: i.name.trim(), qty: i.qty || 0, unit_price: Number(i.unit_price) || 0, product_id: i.product_id })),
  }
  saving.value = true
  try {
    if (mode.value === 'create') {
      q.value = await createQuotation({ customer_id: form.customer.id, ...payload })
      toast(`已存成草稿 ${q.value.no}`, 'success')
    } else {
      q.value = await updateQuotation(q.value.id, payload)
      toast('已儲存', 'success')
    }
    leaveApproved.value = true
    router.replace(`/quotations/${q.value.id}`)
  } catch (e) {
    errors.items = errorText(e, '存檔失敗，稍後再試')
  } finally {
    saving.value = false
  }
}

// ── 狀態動作（送出、收回、成交、沒成、點錯改回、轉成訂單）──
const ACTIONS = {
  send: { label: '送出' },
  recall: { label: '收回', variant: 'outline', confirm: { title: '收回這張報價單？', description: '狀態回到草擬，客戶手上那份 PDF 視為作廢；改好再送出一次。', confirmText: '收回' } },
  win: { label: '成交' },
  lose: { label: '沒成', variant: 'outline' },
  reopen: { label: '點錯改回', variant: 'outline', confirm: { title: '改回已送出？', description: '結果點錯了就改回已送出，這一步也會記在修改紀錄。', confirmText: '改回已送出' } },
  convert: { label: '轉成訂單' },
}
// 往前走的在前、退一步的在後
const ORDER = ['send', 'win', 'lose', 'convert', 'reopen', 'recall']
const shownActions = computed(() => ORDER.filter((a) => q.value?.actions.includes(a)))
const acting = ref('')
const pending = ref(null)   // 等確認的動作

function ask(action) {
  if (ACTIONS[action].confirm) pending.value = action
  else run(action)
}
async function run(action) {
  pending.value = null
  acting.value = action
  try {
    if (action === 'convert') {
      const o = await convertToOrder(q.value.id)
      toast(`已轉成訂單 ${o.no}`, 'success')
      router.push(`/orders/${o.id}`)
      return
    }
    q.value = await quotationAction(q.value.id, action)
    if (action === 'send') toast(`已送出，PDF 可以下載了`, 'success')
    else toast(`${ACTIONS[action].label}：${q.value.status_display}`, 'success')
  } catch (e) {
    toast(errorText(e))
  } finally {
    acting.value = ''
  }
}

// ── 打到一半離開要攔 ──
const dirty = computed(() => editing.value && !leaveApproved.value && JSON.stringify(form) !== snapshot)
const leaveOpen = ref(false)
let leaveResolve = null
function guardLeave() {
  if (!dirty.value) return true
  leaveOpen.value = true
  return new Promise((resolve) => { leaveResolve = resolve })
}
// 開新單／檢視／編輯共用這個元件，彼此切換是「更新」不是「離開」——兩個都要攔
onBeforeRouteLeave(guardLeave)
onBeforeRouteUpdate(guardLeave)
function answerLeave(ok) {
  leaveOpen.value = false
  leaveResolve?.(ok)
  leaveResolve = null
}
watch(() => route.fullPath, () => { leaveApproved.value = false })
function warnOnUnload(e) { if (dirty.value) e.preventDefault() }
onMounted(() => window.addEventListener('beforeunload', warnOnUnload))
onUnmounted(() => window.removeEventListener('beforeunload', warnOnUnload))

const title = computed(() => (mode.value === 'create' ? '開新單' : q.value ? `報價單 ${q.value.no}（${q.value.status_display}）` : '報價單'))
const cellInput = 'focus:bg-muted/30 h-9 w-full bg-transparent px-3 text-sm outline-none'
</script>

<template>
  <form class="flex min-h-full flex-col" @submit.prevent="save">
    <!-- 表頭：回上一頁 │ 標題（狀態放全形括號）　報價操作：[…]　……　[報價單 PDF] -->
    <div class="flex shrink-0 items-center gap-2">
      <Button as-child variant="outline" size="sm" class="min-w-28 shrink-0 rounded-full">
        <RouterLink :to="mode === 'edit' && q ? `/quotations/${q.id}` : '/quotations'"><ArrowLeft class="size-4" /> 回上一頁</RouterLink>
      </Button>
      <div class="bg-border mx-1 h-6 w-px shrink-0"></div>
      <h1 class="truncate text-lg leading-none font-semibold tracking-tight">{{ title }}</h1>

      <div v-if="mode === 'create' || q" class="ml-10 flex shrink-0 items-center gap-2">
        <span class="text-muted-foreground text-sm">報價操作：</span>
        <template v-if="mode === 'create'">
          <PillButton type="submit" :disabled="saving">存草稿</PillButton>
        </template>
        <template v-else-if="mode === 'edit'">
          <PillButton type="submit" :disabled="saving">儲存</PillButton>
          <Button as-child variant="outline" size="sm" class="min-w-24 rounded-full">
            <RouterLink :to="`/quotations/${q.id}`">取消</RouterLink>
          </Button>
        </template>
        <template v-else>
          <PillButton
            v-for="a in shownActions"
            :key="a"
            type="button"
            :variant="ACTIONS[a].variant || 'default'"
            :disabled="!!acting"
            @click="ask(a)"
          >{{ ACTIONS[a].label }}</PillButton>
          <Button as-child variant="outline" size="sm" class="min-w-24 rounded-full">
            <RouterLink :to="`/quotations/${q.id}/edit`">編輯</RouterLink>
          </Button>
        </template>
      </div>

      <Button v-if="mode === 'view' && q && q.status !== 'draft'" as-child variant="outline" size="sm" class="ml-auto shrink-0">
        <a :href="quotationPdfUrl(q.id)" target="_blank" rel="noopener"><FileDown class="size-4" /> 報價單 PDF</a>
      </Button>
    </div>

    <LoadingState v-if="loading" class="mt-5" />
    <div v-else-if="loadError" class="bg-card text-destructive mt-5 rounded-lg border p-10 text-center text-sm shadow-sm">{{ loadError }}</div>

    <div v-else-if="mode === 'create' || q" class="mt-5 flex min-h-0 flex-1 flex-col gap-4">
      <!-- 報價資訊（框線 descriptions）-->
      <div class="bg-card shrink-0 overflow-hidden rounded-lg border shadow-sm">
        <div class="border-b px-4 py-2.5 text-sm font-semibold">報價資訊</div>
        <dl class="grid grid-cols-1 text-sm sm:grid-cols-2">
          <div class="flex border-b">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">客戶</dt>
            <dd class="min-w-0 flex-1">
              <!-- 開新單才挑得了客戶；單子開了就不能換客戶（照 ns：顯示但停用）-->
              <button
                v-if="mode === 'create'"
                ref="customerBtn"
                type="button"
                class="hover:bg-muted/30 flex h-9 w-full cursor-pointer items-center justify-between gap-2 px-3 text-sm transition-colors"
                :aria-invalid="!!errors.customer"
                :aria-describedby="errors.customer ? 'err-customer' : undefined"
                @click="showCustomerDialog = true"
              >
                <span class="truncate" :class="form.customer ? 'font-medium' : 'text-muted-foreground'">{{ form.customer?.name || '搜尋／選擇客戶…' }}</span>
                <Search class="text-muted-foreground size-4 shrink-0" />
              </button>
              <div v-else class="truncate px-3 py-2 font-medium" :class="mode === 'edit' && 'text-muted-foreground cursor-not-allowed'" :title="q.customer_name">{{ q.customer_name }}</div>
              <p v-if="errors.customer" id="err-customer" class="text-destructive px-3 pb-1.5 text-xs">{{ errors.customer }}</p>
            </dd>
          </div>
          <div class="flex border-b sm:border-l">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">客戶電話</dt>
            <dd class="flex-1 px-3 py-2 tabular-nums">{{ (mode === 'create' ? form.customer?.phone : q.customer_phone) || '—' }}</dd>
          </div>
          <div class="flex border-b">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">有效期限</dt>
            <dd class="flex-1">
              <DatePicker v-if="editing" v-model="form.valid_until" bare placeholder="不設限" />
              <div v-else class="px-3 py-2 tabular-nums">
                {{ q.valid_until ? fmtDate(q.valid_until) : '不設限' }}
                <span v-if="q.valid_until && q.status === 'sent'" class="ml-1" :class="q.is_expired ? 'text-destructive font-medium' : 'text-muted-foreground'">（{{ daysLeftText(q.days_left) }}）</span>
              </div>
            </dd>
          </div>
          <div class="flex border-b sm:border-l">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">付款條件</dt>
            <dd class="min-w-0 flex-1">
              <input v-if="editing" v-model="form.payment_terms" name="payment_terms" :class="cellInput" />
              <div v-else class="truncate px-3 py-2">{{ q.payment_terms || '—' }}</div>
            </dd>
          </div>
          <div class="flex border-b">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">負責人</dt>
            <dd class="flex-1 px-3 py-2">{{ mode === 'create' ? user?.display_name : q.owner_name }}</dd>
          </div>
          <div class="flex border-b sm:border-l">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">送出日</dt>
            <dd class="flex-1 px-3 py-2 tabular-nums">{{ mode === 'create' ? '—' : fmtDate(q.sent_on) }}</dd>
          </div>
          <div v-if="q?.orders?.length" class="flex border-b sm:col-span-2">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">訂單</dt>
            <dd class="flex flex-1 flex-wrap gap-x-4 px-3 py-2">
              <RouterLink v-for="o in q.orders" :key="o.id" :to="`/orders/${o.id}`" class="hover:text-primary tabular-nums hover:underline">
                {{ o.no }}（{{ o.status_display }}）
              </RouterLink>
            </dd>
          </div>
          <div class="flex sm:col-span-2">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">備註</dt>
            <dd class="min-w-0 flex-1">
              <input v-if="editing" v-model="form.note" name="note" :class="cellInput" />
              <div v-else class="px-3 py-2 break-words whitespace-pre-line">{{ q.note || '—' }}</div>
            </dd>
          </div>
        </dl>
      </div>

      <!-- 明細（3-table：表頭／表身／總計共用 colgroup，捲軸只在表身、總計釘底）-->
      <div class="bg-card flex min-h-64 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
        <div class="flex shrink-0 items-center justify-between border-b px-4 py-2.5">
          <span class="text-sm font-semibold">
            明細
            <span v-if="errors.items" class="text-destructive ml-2 text-xs font-normal" role="alert">{{ errors.items }}</span>
          </span>
          <div v-if="editing" class="flex gap-2">
            <Button type="button" variant="outline" size="sm" @click="showProductDialog = true"><Search class="size-4" /> 挑商品</Button>
            <Button type="button" variant="outline" size="sm" @click="addFreeLine"><Plus class="size-4" /> 自由填一行</Button>
          </div>
        </div>
        <div class="scroll-thin bg-card shrink-0 overflow-x-hidden overflow-y-scroll border-b">
          <Table class="table-fixed [&_th]:border-b-0">
            <colgroup><col /><col class="w-32" /><col class="w-36" /><col class="w-32" /><col v-if="editing" class="w-12" /></colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>品名</TableHead>
                <TableHead class="text-right">單價</TableHead>
                <TableHead class="text-center">數量</TableHead>
                <TableHead class="text-right">小計</TableHead>
                <TableHead v-if="editing"></TableHead>
              </TableRow>
            </TableHeader>
          </Table>
        </div>
        <div class="scroll-thin min-h-0 flex-1 overflow-y-scroll">
          <Table class="table-fixed">
            <colgroup><col /><col class="w-32" /><col class="w-36" /><col class="w-32" /><col v-if="editing" class="w-12" /></colgroup>
            <TableBody>
              <template v-if="editing">
                <TableRow v-for="(item, idx) in form.items" :key="idx">
                  <TableCell class="p-0"><input v-model="item.name" data-line-name :aria-label="`第 ${idx + 1} 行品名`" placeholder="打品名" :class="cellInput" /></TableCell>
                  <TableCell class="p-0">
                    <input v-model.number="item.unit_price" inputmode="numeric" :aria-label="`第 ${idx + 1} 行單價`" :class="[cellInput, 'text-right tabular-nums']" />
                  </TableCell>
                  <TableCell class="text-center"><NumberInput v-model="item.qty" :min="1" /></TableCell>
                  <TableCell class="text-right tabular-nums">{{ fmtMoney(lineSubtotal(item)) }}</TableCell>
                  <TableCell class="text-center">
                    <Button type="button" variant="ghost" size="icon-sm" class="text-destructive" :aria-label="`刪除第 ${idx + 1} 行`" :title="`刪除第 ${idx + 1} 行`" @click="removeLine(idx)"><X class="size-4" /></Button>
                  </TableCell>
                </TableRow>
              </template>
              <template v-else>
                <TableRow v-for="(item, idx) in q.items" :key="idx">
                  <TableCell class="truncate" :title="item.name">{{ item.name }}</TableCell>
                  <TableCell class="text-right tabular-nums">{{ fmtMoney(item.unit_price) }}</TableCell>
                  <TableCell class="text-center tabular-nums">{{ Number(item.qty) }}</TableCell>
                  <TableCell class="text-right tabular-nums">{{ fmtMoney(item.subtotal) }}</TableCell>
                </TableRow>
              </template>
              <TableRow v-if="!shownItems.length" class="hover:bg-transparent">
                <TableCell :colspan="editing ? 5 : 4" class="text-muted-foreground py-10 text-center">還沒有品項，按右上「挑商品」或「自由填一行」</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <div class="scroll-thin bg-card shrink-0 overflow-x-hidden overflow-y-scroll border-t">
          <Table class="table-fixed [&_td]:border-b-0">
            <colgroup><col /><col class="w-32" /><col class="w-36" /><col class="w-32" /><col v-if="editing" class="w-12" /></colgroup>
            <TableBody>
              <TableRow class="hover:bg-transparent">
                <TableCell></TableCell>
                <TableCell></TableCell>
                <TableCell class="text-right font-semibold">總額</TableCell>
                <TableCell class="text-right font-semibold tabular-nums">{{ fmtMoney(total) }}</TableCell>
                <TableCell v-if="editing"></TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>

      <!-- 修改紀錄：誰、何時、改了什麼（送出後每一次修改、每一次狀態變化）-->
      <div v-if="q" class="bg-card shrink-0 overflow-hidden rounded-lg border shadow-sm">
        <div class="border-b px-4 py-2.5 text-sm font-semibold">修改紀錄</div>
        <ol v-if="q.logs.length" class="divide-y text-sm">
          <li v-for="(log, i) in q.logs" :key="i" class="flex gap-4 px-4 py-2.5">
            <span class="text-muted-foreground w-36 shrink-0 tabular-nums">{{ fmtDateTime(log.at) }}</span>
            <span class="w-20 shrink-0 truncate">{{ log.actor_name }}</span>
            <span class="w-20 shrink-0 font-medium">{{ log.action }}</span>
            <span class="text-muted-foreground min-w-0 flex-1 break-words whitespace-pre-line">{{ log.detail }}</span>
          </li>
        </ol>
        <p v-else class="text-muted-foreground px-4 py-6 text-center text-sm">還沒有紀錄</p>
      </div>
    </div>

    <CustomerSelectDialog v-model:open="showCustomerDialog" @select="(c) => { form.customer = c; errors.customer = '' }" />
    <ProductSelectDialog v-model:open="showProductDialog" @select="addProduct" />
    <ConfirmDialog
      v-if="pending"
      :open="!!pending"
      v-bind="ACTIONS[pending].confirm"
      @confirm="run(pending)"
      @update:open="(v) => { if (!v) pending = null }"
    />
    <ConfirmDialog
      :open="leaveOpen"
      title="還沒存，確定要離開？"
      description="這一頁改的東西還沒存，離開就不見了。"
      confirm-text="離開"
      cancel-text="留下來"
      destructive
      @confirm="answerLeave(true)"
      @cancel="answerLeave(false)"
    />
  </form>
</template>
