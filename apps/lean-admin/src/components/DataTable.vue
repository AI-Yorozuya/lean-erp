<script setup>
// 清單用的 base table（自家輕量版，不是 shadcn 那個 TanStack DataTable）。
// 把清單表格的「水電」一次包好，頁面只要宣告：欄位(columns) + 一列怎麼畫(#row)，
// 選配再給一根釘右的操作欄(#actions)。捲軸/對齊/底線/空狀態全在元件內。
//
// 為什麼是「表頭一張表、表身一張表、共用 colgroup」：
//   垂直捲軸只長在表身 → 碰不到表頭；表頭右側也 overflow-y-scroll、掛「同一個 .scroll-thin」，
//   預留跟表身捲軸一模一樣寬的空槽 → 兩邊右緣都停在同一條線、欄位與隔線完全對齊（不用硬寫 px）。
//   水平方向表頭不自己捲，由 syncHead() 跟著表身左右捲（欄多到要橫捲才用得到）。
//   表頭底線整條只由外層 wrapper 的 border-b 畫滿（含右邊捲軸槽），所以粗細一致。
import { computed, ref, useSlots } from 'vue'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

const props = defineProps({
  // 一般欄位：{ label, width?, align? }
  //   width：Tailwind 寬度 class（如 'w-28'）；省略 = 吃剩餘寬度（彈性欄，如備註）。
  //   align：'left'(預設) | 'center' | 'right'（只管表頭；表身對齊由 #row 各儲存格自己設）。
  columns: { type: Array, required: true },
  items: { type: Array, default: () => [] },
  rowKey: { type: String, default: 'id' }, // v-for 的 key 取哪個欄位
  loading: { type: Boolean, default: false }, // 載入中就先不顯示「空清單」那列
  emptyText: { type: String, default: '沒有資料' }, // 沒資料時的字（也可用 #empty slot 客製）
  actionsLabel: { type: String, default: '操作' }, // 釘右操作欄的表頭字
  actionsWidth: { type: String, default: 'w-28' }, // 釘右操作欄寬
})

const slots = useSlots()
const hasActions = computed(() => !!slots.actions) // 有給 #actions 才長出釘右的操作欄
const totalCols = computed(() => props.columns.length + (hasActions.value ? 1 : 0))
const alignClass = (a) => (a === 'center' ? 'text-center' : a === 'right' ? 'text-right' : '')

// 表頭/表身兩張表：垂直捲軸只在表身。橫捲時把表頭捲到跟表身一樣的位置。
const headScroll = ref(null)
const bodyScroll = ref(null)
function syncHead() {
  if (headScroll.value && bodyScroll.value) headScroll.value.scrollLeft = bodyScroll.value.scrollLeft
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border">
    <!-- 表頭（不參與垂直捲；右側 overflow-y-scroll 預留捲軸槽，空槽透明看不見）-->
    <div ref="headScroll" class="scroll-thin shrink-0 overflow-x-hidden overflow-y-scroll border-b bg-card">
      <Table class="table-fixed [&_th]:border-b-0">
        <colgroup>
          <col v-for="(col, i) in columns" :key="i" :class="col.width" />
          <col v-if="hasActions" :class="actionsWidth" />
        </colgroup>
        <TableHeader>
          <TableRow>
            <TableHead v-for="(col, i) in columns" :key="i" :class="alignClass(col.align)">{{ col.label }}</TableHead>
            <TableHead v-if="hasActions" class="bg-card sticky right-0 z-20 border-l text-center">{{ actionsLabel }}</TableHead>
          </TableRow>
        </TableHeader>
      </Table>
    </div>
    <!-- 表身（垂直捲軸只在這裡；橫捲同步表頭）-->
    <div ref="bodyScroll" class="scroll-thin min-h-0 flex-1 overflow-x-auto overflow-y-scroll" @scroll="syncHead">
      <Table class="table-fixed">
        <colgroup>
          <col v-for="(col, i) in columns" :key="i" :class="col.width" />
          <col v-if="hasActions" :class="actionsWidth" />
        </colgroup>
        <TableBody>
          <TableRow v-for="item in items" :key="item[rowKey]" class="group">
            <!-- 一般儲存格由頁面提供（順序/數量對齊 columns）-->
            <slot name="row" :item="item" />
            <!-- 釘右操作欄：sticky 機制包在這，頁面只給按鈕 -->
            <TableCell v-if="hasActions" class="bg-card group-hover:bg-muted/50 sticky right-0 z-10 border-l">
              <div class="flex items-center justify-center gap-1">
                <slot name="actions" :item="item" />
              </div>
            </TableCell>
          </TableRow>
          <!-- 空清單（載入中不顯示，避免閃一下「沒有資料」）-->
          <TableRow v-if="!loading && items.length === 0">
            <TableCell :colspan="totalCols" class="text-muted-foreground py-10 text-center">
              <slot name="empty">{{ emptyText }}</slot>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  </div>
</template>
