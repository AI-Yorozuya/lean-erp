<script setup>
// 報價單詳細（系統總覽・頁面 quote_detail）：一個檔管開新單／檢視／編輯（照 ns/top：同一個骨架，只換可編輯的格子）。
// 泳道：選擇客戶 → 新增品項 → 確認建立（草稿，sp_create）→ 匯出 PDF（已送出，sp_pdf）→ 傳給客戶。
// 規矩：客戶只能選取（rule_customer_pick）、單價照商品帶入不能改（rule_price_from_product）、
// 滿十萬免運（rule_free_shipping）、已送出的報價單不能改（rule_sent_locked）。
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Plus, Search, X } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import NumberInput from '@/components/NumberInput.vue'
import PillButton from '@/components/PillButton.vue'
import LoadingState from '@/components/LoadingState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CustomerSelectDialog from '@/components/CustomerSelectDialog.vue'
import ProductSelectDialog from '@/components/ProductSelectDialog.vue'
import { getQuotation, createQuotation, updateQuotation, exportQuotationPdf, errorText } from '@/api'
import { useSession } from '@/session'
import { toast } from '@/lib/toast'
import { fmtMoney, fmtDate } from '@/lib/format'
import { useLeaveGuard } from '@/lib/useLeaveGuard'

const FREE_SHIPPING = 100000

const route = useRoute()
const router = useRouter()
const { user } = useSession()

const ROUTES = ['quotation-new', 'quotation-detail', 'quotation-edit']
const mode = computed(() => (route.name === 'quotation-new' ? 'create' : route.name === 'quotation-edit' ? 'edit' : 'view'))
const editing = computed(() => mode.value !== 'view')

// ── 資料 ──
const q = ref(null)
const loading = ref(false)
const loadError = ref('')
const form = reactive({ customer: null, items: [] })   // items：{ product_id, model, name, unit_price, qty }
const snapshot = ref('')
const takeSnapshot = () => { snapshot.value = JSON.stringify(form) }

function fillForm(src) {
  form.customer = src ? { id: src.customer_id, name: src.customer_name, contact: src.customer_contact } : null
  form.items = src ? src.items.map((i) => ({ product_id: i.product_id, model: i.model, name: i.name, unit_price: i.unit_price, qty: i.qty })) : []
  takeSnapshot()
}

async function load() {
  if (!ROUTES.includes(route.name)) return
  errors.customer = errors.items = ''
  if (mode.value === 'create') {
    q.value = null
    fillForm(null)
    return
  }
  const id = Number(route.params.id)
  if (q.value?.id !== id) {
    loading.value = true
    loadError.value = ''
    try {
      q.value = await getQuotation(id)
    } catch (e) {
      loadError.value = e.response?.status === 404 ? '找不到這張報價單' : errorText(e, '撈不到這張報價單，稍後再試')
    } finally {
      loading.value = false
    }
  }
  if (q.value && mode.value === 'edit' && q.value.status !== 'draft') {
    toast('已送出的報價單不能改')
    router.replace(`/quotations/${q.value.id}`)
    return
  }
  if (q.value && editing.value) fillForm(q.value)
}
watch(() => route.fullPath, load)
onMounted(load)

// ── 品項（編輯中）──
const shownItems = computed(() => (editing.value ? form.items : q.value?.items ?? []))
const total = computed(() => shownItems.value.reduce((s, i) => s + i.unit_price * (Number(i.qty) || 0), 0))
const freeShipping = computed(() => total.value >= FREE_SHIPPING)
const showCustomerDialog = ref(false)
const showProductDialog = ref(false)

function pickCustomer(c) {
  form.customer = c
  errors.customer = ''
}
// 新增品項：挑同一個商品就把數量加一（照原型）
function addProduct(p) {
  const line = form.items.find((i) => i.product_id === p.id)
  if (line) line.qty += 1
  else form.items.push({ product_id: p.id, model: p.model, name: p.name, unit_price: p.price, qty: 1 })
  errors.items = ''
}
const removeLine = (idx) => form.items.splice(idx, 1)

// ── 確認建立／儲存 ──
const errors = reactive({ customer: '', items: '' })
const customerBtn = ref(null)
const saving = ref(false)
const guard = useLeaveGuard(() => editing.value && JSON.stringify(form) !== snapshot.value)

async function save() {
  errors.customer = form.customer ? '' : '還沒選客戶'
  errors.items = form.items.length ? '' : '至少要有一個品項'
  if (errors.customer) { customerBtn.value?.focus(); return }
  if (errors.items) return
  const items = form.items.map((i) => ({ product_id: i.product_id, qty: Number(i.qty) || 0 }))
  saving.value = true
  try {
    if (mode.value === 'create') {
      const created = await createQuotation({ customer_id: form.customer.id, items })
      toast(`已建立 ${created.no}`, 'success')
      guard.approve()
      router.push('/quotations')        // sp_create：成功進報價單列表，第一列是這張新單
    } else {
      q.value = await updateQuotation(q.value.id, { items })
      toast('已儲存', 'success')
      guard.approve()
      router.replace(`/quotations/${q.value.id}`)
    }
  } catch (e) {
    errors.items = errorText(e, '存檔失敗，稍後再試')   // 資料留在頁上
  } finally {
    saving.value = false
  }
}
function cancel() {
  guard.approve()                      // 取消＝丟掉，不再問一次
  router.push(mode.value === 'edit' ? `/quotations/${q.value.id}` : '/quotations')
}

// ── 匯出 PDF（草稿 → 已送出；已送出的再匯出只是再下載）──
const exporting = ref(false)
async function exportPdf() {
  exporting.value = true
  try {
    const wasDraft = q.value.status === 'draft'
    const blob = await exportQuotationPdf(q.value.id)
    const url = URL.createObjectURL(blob)
    const a = Object.assign(document.createElement('a'), { href: url, download: `${q.value.no}.pdf` })
    a.click()
    URL.revokeObjectURL(url)
    q.value = await getQuotation(q.value.id)
    toast(wasDraft ? `已匯出 PDF，${q.value.no} 已送出` : '已重新下載 PDF', 'success')
  } catch (e) {
    toast(errorText(e, '匯出失敗，稍後再試'))
  } finally {
    exporting.value = false
  }
}

const title = computed(() => (mode.value === 'create' ? '開新單' : q.value ? `報價單 ${q.value.no}（${q.value.status_display}）` : '報價單'))
const cols = computed(() => (editing.value ? ['w-32', '', 'w-28', 'w-36', 'w-32', 'w-12'] : ['w-32', '', 'w-28', 'w-24', 'w-32']))
</script>

<template>
  <form class="flex min-h-full flex-col" @submit.prevent="save">
    <!-- 表頭：回上一頁 │ 標題（狀態放全形括號）　報價操作：[…] -->
    <div class="flex shrink-0 items-center gap-2">
      <Button as-child variant="outline" size="sm" class="min-w-28 shrink-0 rounded-full">
        <RouterLink :to="mode === 'edit' && q ? `/quotations/${q.id}` : '/quotations'"><ArrowLeft class="size-4" /> 回上一頁</RouterLink>
      </Button>
      <div class="bg-border mx-1 h-6 w-px shrink-0"></div>
      <h1 class="truncate text-lg leading-none font-semibold tracking-tight">{{ title }}</h1>

      <div v-if="mode === 'create' || q" class="ml-10 flex shrink-0 items-center gap-2">
        <span class="text-muted-foreground text-sm">報價操作：</span>
        <template v-if="editing">
          <PillButton type="submit" :disabled="saving">{{ mode === 'create' ? '確認建立' : '儲存' }}</PillButton>
          <PillButton type="button" variant="outline" @click="cancel">取消</PillButton>
        </template>
        <template v-else>
          <PillButton type="button" :disabled="exporting" @click="exportPdf">匯出 PDF</PillButton>
          <Button v-if="q.status === 'draft'" as-child variant="outline" size="sm" class="min-w-24 rounded-full">
            <RouterLink :to="`/quotations/${q.id}/edit`">編輯</RouterLink>
          </Button>
          <PillButton v-else type="button" variant="outline" disabled title="已送出的報價單不能改">編輯</PillButton>
        </template>
      </div>
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
              <!-- 開新單才選得了客戶；單子開了就不能換客戶（照 ns：顯示但停用）-->
              <button
                v-if="mode === 'create'"
                ref="customerBtn"
                type="button"
                class="hover:bg-muted/30 flex h-9 w-full cursor-pointer items-center justify-between gap-2 px-3 text-sm transition-colors"
                :aria-invalid="!!errors.customer"
                :aria-describedby="errors.customer ? 'err-customer' : undefined"
                @click="showCustomerDialog = true"
              >
                <span class="truncate" :class="form.customer ? 'font-medium' : 'text-muted-foreground'">{{ form.customer?.name || '選擇客戶…' }}</span>
                <Search class="text-muted-foreground size-4 shrink-0" />
              </button>
              <div v-else class="truncate px-3 py-2 font-medium" :class="mode === 'edit' && 'text-muted-foreground cursor-not-allowed'" :title="q.customer_name">{{ q.customer_name }}</div>
              <p v-if="errors.customer" id="err-customer" class="text-destructive px-3 pb-1.5 text-xs" role="alert">{{ errors.customer }}</p>
            </dd>
          </div>
          <div class="flex border-b sm:border-l">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">聯絡人</dt>
            <dd class="flex-1 truncate px-3 py-2">{{ (mode === 'create' ? form.customer?.contact : q.customer_contact) || '—' }}</dd>
          </div>
          <div class="flex border-b">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">日期</dt>
            <dd class="flex-1 px-3 py-2 tabular-nums">{{ mode === 'create' ? fmtDate(new Date().toLocaleDateString('sv')) : fmtDate(q.date) }}</dd>
          </div>
          <div class="flex border-b sm:border-l">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">業務</dt>
            <dd class="flex-1 px-3 py-2">{{ mode === 'create' ? user?.display_name : q.sales_name }}</dd>
          </div>
          <div class="flex sm:col-span-2">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">送出日期</dt>
            <dd class="flex-1 px-3 py-2 tabular-nums">{{ mode === 'create' ? '—' : fmtDate(q.sent_at) }}</dd>
          </div>
        </dl>
      </div>

      <!-- 品項（3-table：表頭／表身／合計共用 colgroup，捲軸只在表身、合計釘底）-->
      <div class="bg-card flex min-h-64 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
        <div class="flex shrink-0 items-center justify-between border-b px-4 py-2.5">
          <span class="text-sm font-semibold">
            品項
            <span v-if="errors.items" class="text-destructive ml-2 text-xs font-normal" role="alert">{{ errors.items }}</span>
          </span>
          <Button v-if="editing" type="button" variant="outline" size="sm" @click="showProductDialog = true"><Plus class="size-4" /> 新增品項</Button>
        </div>
        <div class="scroll-thin bg-card shrink-0 overflow-x-hidden overflow-y-scroll border-b">
          <Table class="table-fixed [&_th]:border-b-0">
            <colgroup><col v-for="(w, i) in cols" :key="i" :class="w" /></colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>型號</TableHead>
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
            <colgroup><col v-for="(w, i) in cols" :key="i" :class="w" /></colgroup>
            <TableBody>
              <TableRow v-for="(item, idx) in shownItems" :key="item.product_id">
                <TableCell class="tabular-nums">{{ item.model }}</TableCell>
                <TableCell class="truncate" :title="item.name">{{ item.name }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ fmtMoney(item.unit_price) }}</TableCell>
                <TableCell class="text-center tabular-nums">
                  <NumberInput v-if="editing" v-model="item.qty" :min="1" />
                  <template v-else>{{ item.qty }}</template>
                </TableCell>
                <TableCell class="text-right tabular-nums">{{ fmtMoney(item.unit_price * (Number(item.qty) || 0)) }}</TableCell>
                <TableCell v-if="editing" class="text-center">
                  <Button type="button" variant="ghost" size="icon-sm" class="text-destructive" :aria-label="`移除 ${item.model}`" :title="`移除 ${item.model}`" @click="removeLine(idx)"><X class="size-4" /></Button>
                </TableCell>
              </TableRow>
              <TableRow v-if="!shownItems.length" class="hover:bg-transparent">
                <TableCell :colspan="cols.length" class="text-muted-foreground py-10 text-center">還沒有品項，按右上「新增品項」</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <div class="scroll-thin bg-card shrink-0 overflow-x-hidden overflow-y-scroll border-t">
          <Table class="table-fixed [&_td]:border-b-0">
            <colgroup><col v-for="(w, i) in cols" :key="i" :class="w" /></colgroup>
            <TableBody>
              <TableRow class="hover:bg-transparent">
                <TableCell :colspan="4" class="text-muted-foreground text-right">運費</TableCell>
                <TableCell class="text-right" :class="freeShipping ? 'font-medium' : 'text-muted-foreground'">{{ freeShipping ? '免運' : '運費另計' }}</TableCell>
                <TableCell v-if="editing"></TableCell>
              </TableRow>
              <TableRow class="hover:bg-transparent">
                <TableCell :colspan="4" class="text-right font-semibold">總額</TableCell>
                <TableCell class="text-right font-semibold tabular-nums">{{ fmtMoney(total) }}</TableCell>
                <TableCell v-if="editing"></TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>
    </div>

    <CustomerSelectDialog v-model:open="showCustomerDialog" @select="pickCustomer" />
    <ProductSelectDialog v-model:open="showProductDialog" @select="addProduct" />
    <ConfirmDialog :open="guard.leaveOpen.value" title="還沒存，確定要離開？" description="這一頁改的東西還沒存，離開就不見了。"
      confirm-text="離開" cancel-text="留下來" destructive @confirm="guard.answer(true)" @cancel="guard.answer(false)" />
  </form>
</template>
