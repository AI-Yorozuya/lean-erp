<script setup>
// 業績頁（系統總覽・頁面 stats_report，規格 sp_stats）：老闆看每個月的報價張數、報價總額。
// 從已送出的報價單算，草稿不算；一個月一列、新的月份在上面；沒有送出報價單的月份不列。
// 只看不改：這一頁沒有任何會改資料的按鈕（rule_boss_view_only）。
import { onMounted, ref } from 'vue'
import { TableCell } from '@/components/ui/table'
import DataTable from '@/components/DataTable.vue'
import { getStats, errorText } from '@/api'
import { fmtMoney } from '@/lib/format'

const columns = [
  { label: '月份' },
  { label: '報價張數', width: 'w-32', align: 'right' },
  { label: '報價總額', width: 'w-40', align: 'right' },
]
const monthFmt = new Intl.DateTimeFormat('zh-TW', { year: 'numeric', month: 'long' })
const fmtMonth = (s) => monthFmt.format(new Date(`${s}T00:00:00`))

const rows = ref([])
const loading = ref(true)
const loadError = ref('')

onMounted(async () => {
  try {
    rows.value = (await getStats()).map((r) => ({ ...r, id: r.month }))
  } catch (e) {
    loadError.value = errorText(e, '撈不到業績，確認後端有沒有開著，再重新整理一次')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="flex h-full flex-col">
    <h1 class="shrink-0 text-lg leading-none font-semibold tracking-tight">業績</h1>
    <div class="bg-card mt-5 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border shadow-sm">
      <div class="flex min-h-0 flex-1 flex-col p-5">
        <DataTable :items="rows" :columns="columns" :loading="loading">
          <template #row="{ item: r }">
            <TableCell class="font-medium tabular-nums">{{ fmtMonth(r.month) }}</TableCell>
            <TableCell class="text-right tabular-nums">{{ r.quote_count }} 張</TableCell>
            <TableCell class="text-right tabular-nums">{{ fmtMoney(r.quote_total) }}</TableCell>
          </template>
          <template #empty>
            <span v-if="loadError" class="text-destructive">{{ loadError }}</span>
            <template v-else>還沒有送出的報價單</template>
          </template>
        </DataTable>
      </div>
    </div>
  </div>
</template>
