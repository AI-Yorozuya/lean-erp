<script setup>
// 月份 picker：`YYYY-MM` 進、`YYYY-MM` 出。行事曆用它做「粗調」（跳到某個月），
// 細調（前後一週）交給旁邊的箭頭。
//
// 樣式與互動刻意跟 DatePicker.vue 同一套（reka-ui Popover + shadcn token），
// 只是把「日格」換成「12 個月格」，年份用 ‹ › 換。
// 為什麼不用原生 <input type="month">：它跟著瀏覽器語系顯示 "July 2026"，
// 跟整個中文後台打架，而且各家樣式不一致。
import { computed, ref, watch } from 'vue'
import { PopoverRoot, PopoverTrigger, PopoverPortal, PopoverContent } from 'reka-ui'
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from '@lucide/vue'

const props = defineProps({
  modelValue: { type: String, default: '' },   // 'YYYY-MM'
  disabled: Boolean,
})
const emit = defineEmits(['update:modelValue'])

const today = new Date()
const open = ref(false)

function parse(v) {
  const m = String(v || '').match(/^(\d{4})-(\d{1,2})$/)
  return m ? { year: Number(m[1]), month: Number(m[2]) } : null
}
const fmt = (y, m) => `${y}-${String(m).padStart(2, '0')}`

const selected = computed(() => parse(props.modelValue))
const viewYear = ref(selected.value?.year ?? today.getFullYear())

// 外面翻週翻過年時，popover 打開要落在正確的年份。
watch(() => props.modelValue, (v) => {
  const p = parse(v)
  if (p) viewYear.value = p.year
})

const label = computed(() => {
  const s = selected.value
  return s ? `${s.year} 年 ${s.month} 月` : '選月份'
})
const isCurrentMonth = (y, m) => y === today.getFullYear() && m === today.getMonth() + 1

function pick(m) {
  emit('update:modelValue', fmt(viewYear.value, m))
  open.value = false
}
function pickThisMonth() {
  viewYear.value = today.getFullYear()
  emit('update:modelValue', fmt(today.getFullYear(), today.getMonth() + 1))
  open.value = false
}
</script>

<template>
  <PopoverRoot v-model:open="open">
    <PopoverTrigger as-child>
      <button
        type="button"
        :disabled="disabled"
        class="hover:bg-accent data-[state=open]:bg-accent inline-flex h-9 cursor-pointer items-center gap-2 px-3 text-sm transition-colors focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
      >
        <CalendarIcon class="text-muted-foreground size-4 shrink-0" />
        <span class="whitespace-nowrap tabular-nums">{{ label }}</span>
      </button>
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        :side-offset="6"
        align="start"
        class="bg-popover text-popover-foreground z-50 w-[260px] rounded-md border p-3 shadow-md outline-none"
      >
        <!-- 年份列 -->
        <div class="mb-2 flex items-center justify-between">
          <button
            type="button"
            class="text-muted-foreground hover:bg-muted hover:text-foreground flex size-7 cursor-pointer items-center justify-center rounded"
            title="前一年"
            @click="viewYear -= 1"
          ><ChevronLeft class="size-4" /></button>
          <span class="text-sm font-semibold tabular-nums">{{ viewYear }} 年</span>
          <button
            type="button"
            class="text-muted-foreground hover:bg-muted hover:text-foreground flex size-7 cursor-pointer items-center justify-center rounded"
            title="後一年"
            @click="viewYear += 1"
          ><ChevronRight class="size-4" /></button>
        </div>

        <!-- 12 個月 -->
        <div class="grid grid-cols-3 gap-1">
          <button
            v-for="m in 12"
            :key="m"
            type="button"
            :class="[
              'flex h-9 cursor-pointer items-center justify-center rounded text-xs transition-colors',
              selected && selected.year === viewYear && selected.month === m
                ? 'bg-primary text-primary-foreground hover:bg-primary font-semibold'
                : isCurrentMonth(viewYear, m)
                  ? 'bg-muted font-semibold'
                  : 'hover:bg-accent hover:text-accent-foreground',
            ]"
            @click="pick(m)"
          >{{ m }} 月</button>
        </div>

        <div class="mt-2 border-t pt-2">
          <button
            type="button"
            class="text-muted-foreground hover:text-foreground w-full cursor-pointer rounded py-1 text-xs transition-colors"
            @click="pickThisMonth"
          >本月</button>
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
