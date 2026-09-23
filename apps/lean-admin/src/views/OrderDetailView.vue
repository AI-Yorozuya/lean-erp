<script setup>
// 訂單詳細頁（intents/轉成訂單.md、intents/訂單推進.md）：推進、退回、作廢、看修改紀錄。
// 骨架跟報價單詳細頁同一套；訂單明細是轉單當下複製的一份，這頁不改明細。
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ArrowLeft } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import PillButton from '@/components/PillButton.vue'
import LoadingState from '@/components/LoadingState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { getOrder, orderAction, errorText } from '@/api'
import { toast } from '@/lib/toast'
import { fmtMoney, fmtDate, fmtDay, fmtDateTime } from '@/lib/format'

const route = useRoute()
const o = ref(null)
const loading = ref(false)
const loadError = ref('')

async function load() {
  if (route.name !== 'order-detail') return
  const id = Number(route.params.id)
  if (o.value?.id === id) return
  loading.value = true
  loadError.value = ''
  try {
    o.value = await getOrder(id)
  } catch (e) {
    loadError.value = e.response?.status === 404 ? '找不到這張訂單' : errorText(e, '撈不到這張訂單，稍後再試')
  } finally {
    loading.value = false
  }
}
watch(() => route.params.id, load)
onMounted(load)

// 按鈕照後端給的 actions 出：狀態不對的動作不出現（處理中沒有作廢鍵）
const ACTIONS = {
  start: { label: '開始處理' },
  finish: { label: '完成' },
  back: { label: '退回待處理', variant: 'outline' },
  reopen: { label: '點錯改回', variant: 'outline', confirm: { title: '改回處理中？', description: '完成點錯了就改回處理中，這一步也會記在修改紀錄。', confirmText: '改回處理中' } },
  void: {
    label: '作廢', variant: 'ghost', class: 'text-destructive',
    confirm: { title: '作廢這張訂單？', description: '訂單留著一筆作廢紀錄，不會刪掉；報價單回到已成交，可以再轉一張新的。', confirmText: '作廢', destructive: true },
  },
}
const acting = ref('')
const pending = ref(null)

function ask(action) {
  if (ACTIONS[action].confirm) pending.value = action
  else run(action)
}
async function run(action) {
  pending.value = null
  acting.value = action
  try {
    o.value = await orderAction(o.value.id, action)
    toast(`${ACTIONS[action].label}：${o.value.status_display}`, 'success')
  } catch (e) {
    toast(errorText(e))
  } finally {
    acting.value = ''
  }
}
</script>

<template>
  <div class="flex min-h-full flex-col">
    <div class="flex shrink-0 items-center gap-2">
      <Button as-child variant="outline" size="sm" class="min-w-28 shrink-0 rounded-full">
        <RouterLink to="/orders"><ArrowLeft class="size-4" /> 回上一頁</RouterLink>
      </Button>
      <div class="bg-border mx-1 h-6 w-px shrink-0"></div>
      <h1 class="truncate text-lg leading-none font-semibold tracking-tight">{{ o ? `訂單 ${o.no}（${o.status_display}）` : '訂單' }}</h1>
      <div v-if="o?.actions.length" class="ml-10 flex shrink-0 items-center gap-2">
        <span class="text-muted-foreground text-sm">訂單操作：</span>
        <PillButton
          v-for="a in o.actions"
          :key="a"
          :variant="ACTIONS[a].variant || 'default'"
          :class="ACTIONS[a].class"
          :disabled="!!acting"
          @click="ask(a)"
        >{{ ACTIONS[a].label }}</PillButton>
      </div>
    </div>

    <LoadingState v-if="loading" class="mt-5" />
    <div v-else-if="loadError" class="bg-card text-destructive mt-5 rounded-lg border p-10 text-center text-sm shadow-sm">{{ loadError }}</div>

    <div v-else-if="o" class="mt-5 flex min-h-0 flex-1 flex-col gap-4">
      <div class="bg-card shrink-0 overflow-hidden rounded-lg border shadow-sm">
        <div class="border-b px-4 py-2.5 text-sm font-semibold">訂單資訊</div>
        <dl class="grid grid-cols-1 text-sm sm:grid-cols-2">
          <div class="flex border-b">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">客戶</dt>
            <dd class="min-w-0 flex-1 truncate px-3 py-2 font-medium" :title="o.customer_name">{{ o.customer_name }}</dd>
          </div>
          <div class="flex border-b sm:border-l">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">來源報價單</dt>
            <dd class="flex-1 px-3 py-2 tabular-nums">
              <RouterLink :to="`/quotations/${o.quotation_id}`" class="hover:text-primary hover:underline">{{ o.quotation_no }}</RouterLink>
            </dd>
          </div>
          <div class="flex">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">轉單日</dt>
            <dd class="flex-1 px-3 py-2 tabular-nums">{{ fmtDay(o.created_at) }}</dd>
          </div>
          <div class="flex border-t sm:border-t-0 sm:border-l">
            <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">預計交付</dt>
            <dd class="flex-1 px-3 py-2 tabular-nums">{{ fmtDate(o.expected_delivery) }}</dd>
          </div>
        </dl>
      </div>

      <div class="bg-card flex min-h-64 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
        <div class="shrink-0 border-b px-4 py-2.5 text-sm font-semibold">明細</div>
        <div class="scroll-thin bg-card shrink-0 overflow-x-hidden overflow-y-scroll border-b">
          <Table class="table-fixed [&_th]:border-b-0">
            <colgroup><col /><col class="w-32" /><col class="w-36" /><col class="w-32" /></colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>品名</TableHead>
                <TableHead class="text-right">單價</TableHead>
                <TableHead class="text-center">數量</TableHead>
                <TableHead class="text-right">小計</TableHead>
              </TableRow>
            </TableHeader>
          </Table>
        </div>
        <div class="scroll-thin min-h-0 flex-1 overflow-y-scroll">
          <Table class="table-fixed">
            <colgroup><col /><col class="w-32" /><col class="w-36" /><col class="w-32" /></colgroup>
            <TableBody>
              <TableRow v-for="(item, idx) in o.items" :key="idx">
                <TableCell class="truncate" :title="item.name">{{ item.name }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ fmtMoney(item.unit_price) }}</TableCell>
                <TableCell class="text-center tabular-nums">{{ Number(item.qty) }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ fmtMoney(item.subtotal) }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <div class="scroll-thin bg-card shrink-0 overflow-x-hidden overflow-y-scroll border-t">
          <Table class="table-fixed [&_td]:border-b-0">
            <colgroup><col /><col class="w-32" /><col class="w-36" /><col class="w-32" /></colgroup>
            <TableBody>
              <TableRow class="hover:bg-transparent">
                <TableCell></TableCell>
                <TableCell></TableCell>
                <TableCell class="text-right font-semibold">總額</TableCell>
                <TableCell class="text-right font-semibold tabular-nums">{{ fmtMoney(o.total) }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>

      <div class="bg-card shrink-0 overflow-hidden rounded-lg border shadow-sm">
        <div class="border-b px-4 py-2.5 text-sm font-semibold">修改紀錄</div>
        <ol v-if="o.logs.length" class="divide-y text-sm">
          <li v-for="(log, i) in o.logs" :key="i" class="flex gap-4 px-4 py-2.5">
            <span class="text-muted-foreground w-36 shrink-0 tabular-nums">{{ fmtDateTime(log.at) }}</span>
            <span class="w-20 shrink-0 truncate">{{ log.actor_name }}</span>
            <span class="w-20 shrink-0 font-medium">{{ log.action }}</span>
            <span class="text-muted-foreground min-w-0 flex-1 break-words whitespace-pre-line">{{ log.detail }}</span>
          </li>
        </ol>
        <p v-else class="text-muted-foreground px-4 py-6 text-center text-sm">還沒有紀錄</p>
      </div>
    </div>

    <ConfirmDialog
      v-if="pending"
      :open="!!pending"
      v-bind="ACTIONS[pending].confirm"
      @confirm="run(pending)"
      @update:open="(v) => { if (!v) pending = null }"
    />
  </div>
</template>
