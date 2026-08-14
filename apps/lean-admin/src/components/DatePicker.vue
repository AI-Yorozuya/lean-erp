<script setup>
// 含年份的日期 picker（day/month/year 三視圖）。移植自 top-admin BaseDatePicker，
// 改用本 repo 的 reka-ui Popover + @lucide/vue + shadcn design token。
// modelValue: 'YYYY-MM-DD' 字串 / ''（清除）。
import { ref, computed, watch } from 'vue'
import { PopoverRoot, PopoverTrigger, PopoverPortal, PopoverContent } from 'reka-ui'
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from '@lucide/vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '選日期' },
  disabled: Boolean,
  min: { type: String, default: '' },
  max: { type: String, default: '' },
  // bare：拿掉邊框/底色/圓角，讓 picker 無縫嵌進描述格（訂單編輯的格子內編輯用）。
  bare: Boolean,
})
const emit = defineEmits(['update:modelValue'])

const triggerClass = computed(() =>
  props.bare
    ? 'hover:bg-muted/30 focus:bg-muted/30 inline-flex h-9 w-full cursor-pointer items-center gap-2 px-3 text-sm transition-colors focus:outline-none disabled:cursor-not-allowed disabled:opacity-60'
    : 'border-input bg-background hover:bg-muted/50 focus:border-ring focus:ring-ring/50 data-[state=open]:border-ring inline-flex h-9 w-full cursor-pointer items-center gap-2 rounded-md border px-3 text-sm transition-colors focus:outline-none focus:ring-[3px] disabled:cursor-not-allowed disabled:opacity-60',
)

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

function parse(val) {
  if (!val) return null
  const m = String(val).match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
  if (!m) return null
  return { year: Number(m[1]), month: Number(m[2]), day: Number(m[3]) }
}
function fmt(y, m, d) {
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

const open = ref(false)
const today = new Date()
const initParsed = parse(props.modelValue)
const viewYear = ref(initParsed?.year ?? today.getFullYear())
const viewMonth = ref(initParsed?.month ?? (today.getMonth() + 1))
const viewMode = ref('day')

watch(open, (o) => { if (o) viewMode.value = 'day' })
watch(() => props.modelValue, (v) => {
  const p = parse(v)
  if (p) { viewYear.value = p.year; viewMonth.value = p.month }
})

const yearGridStart = computed(() => Math.floor((viewYear.value - 1) / 12) * 12 + 1)
const yearGrid = computed(() => Array.from({ length: 12 }, (_, i) => yearGridStart.value + i))
const yearGridLabel = computed(() => `${yearGridStart.value} ~ ${yearGridStart.value + 11}`)
const MONTH_NAMES = Array.from({ length: 12 }, (_, i) => `${i + 1} 月`)

function pickYear(y) { viewYear.value = y; viewMode.value = 'day' }
function pickMonth(m) { viewMonth.value = m; viewMode.value = 'day' }
function prevYearGrid() { viewYear.value -= 12 }
function nextYearGrid() { viewYear.value += 12 }

const selected = computed(() => parse(props.modelValue))
const displayText = computed(() => props.modelValue || props.placeholder)

function daysInMonth(y, m) { return new Date(y, m, 0).getDate() }
const minDate = computed(() => parse(props.min))
const maxDate = computed(() => parse(props.max))
function compareYMD(a, b) {
  if (a.year !== b.year) return a.year - b.year
  if (a.month !== b.month) return a.month - b.month
  return a.day - b.day
}
function isOutOfRange(y, m, d) {
  const ymd = { year: y, month: m, day: d }
  if (minDate.value && compareYMD(ymd, minDate.value) < 0) return true
  if (maxDate.value && compareYMD(ymd, maxDate.value) > 0) return true
  return false
}

const calendarCells = computed(() => {
  const y = viewYear.value
  const m = viewMonth.value
  const total = daysInMonth(y, m)
  const firstDayWeekday = new Date(y, m - 1, 1).getDay()
  const sel = selected.value
  const isCurMonth = today.getFullYear() === y && today.getMonth() + 1 === m
  const cells = []
  for (let i = 0; i < firstDayWeekday; i++) cells.push({ key: `empty-${i}`, empty: true })
  for (let d = 1; d <= total; d++) {
    cells.push({
      key: `day-${d}`, day: d,
      isSelected: sel && sel.year === y && sel.month === m && sel.day === d,
      isToday: isCurMonth && today.getDate() === d,
      disabled: isOutOfRange(y, m, d),
    })
  }
  return cells
})

function prevMonth() { if (viewMonth.value === 1) { viewMonth.value = 12; viewYear.value -= 1 } else viewMonth.value -= 1 }
function nextMonth() { if (viewMonth.value === 12) { viewMonth.value = 1; viewYear.value += 1 } else viewMonth.value += 1 }
function prevYear() { viewYear.value -= 1 }
function nextYear() { viewYear.value += 1 }

function pickDay(d) {
  if (!d || isOutOfRange(viewYear.value, viewMonth.value, d)) return
  emit('update:modelValue', fmt(viewYear.value, viewMonth.value, d))
  open.value = false
}
function pickToday() {
  const t = new Date()
  if (isOutOfRange(t.getFullYear(), t.getMonth() + 1, t.getDate())) return
  emit('update:modelValue', fmt(t.getFullYear(), t.getMonth() + 1, t.getDate()))
  viewYear.value = t.getFullYear(); viewMonth.value = t.getMonth() + 1
  open.value = false
}
function clearValue() { emit('update:modelValue', ''); open.value = false }
</script>

<template>
  <PopoverRoot v-model:open="open">
    <PopoverTrigger as-child>
      <button
        type="button"
        :disabled="disabled"
        :class="triggerClass"
      >
        <CalendarIcon class="text-muted-foreground size-4 shrink-0" />
        <span class="flex-1 text-left" :class="!modelValue && 'text-muted-foreground'">{{ displayText }}</span>
      </button>
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        :side-offset="6"
        align="start"
        class="bg-popover text-popover-foreground z-50 w-[280px] rounded-md border p-3 shadow-md outline-none"
      >
        <!-- DAY -->
        <template v-if="viewMode === 'day'">
          <div class="mb-2 flex items-center justify-between">
            <button type="button" class="text-muted-foreground hover:bg-muted hover:text-foreground flex size-7 cursor-pointer items-center justify-center rounded" @click="prevMonth"><ChevronLeft class="size-4" /></button>
            <div class="flex items-center gap-1">
              <button type="button" class="hover:bg-muted hover:text-primary cursor-pointer rounded px-2 py-1 text-sm font-semibold" @click="viewMode = 'year'">{{ viewYear }} 年</button>
              <button type="button" class="hover:bg-muted hover:text-primary cursor-pointer rounded px-2 py-1 text-sm font-semibold" @click="viewMode = 'month'">{{ viewMonth }} 月</button>
            </div>
            <button type="button" class="text-muted-foreground hover:bg-muted hover:text-foreground flex size-7 cursor-pointer items-center justify-center rounded" @click="nextMonth"><ChevronRight class="size-4" /></button>
          </div>
          <div class="mb-1 grid grid-cols-7 gap-0.5">
            <span v-for="w in WEEKDAYS" :key="w" class="text-muted-foreground flex h-6 items-center justify-center text-[11px] font-semibold">{{ w }}</span>
          </div>
          <div class="grid grid-cols-7 gap-0.5">
            <button
              v-for="cell in calendarCells"
              :key="cell.key"
              type="button"
              :disabled="cell.empty || cell.disabled"
              :class="[
                'flex h-8 w-full cursor-pointer items-center justify-center rounded text-xs transition-colors',
                cell.empty && 'invisible cursor-default',
                !cell.empty && cell.disabled && 'text-muted-foreground/40 cursor-not-allowed',
                !cell.empty && !cell.disabled && !cell.isSelected && 'hover:bg-accent hover:text-accent-foreground',
                cell.isToday && !cell.isSelected && 'bg-muted font-semibold',
                cell.isSelected && 'bg-primary text-primary-foreground hover:bg-primary font-semibold',
              ]"
              @click="pickDay(cell.day)"
            >{{ cell.day || '' }}</button>
          </div>
        </template>

        <!-- MONTH -->
        <template v-else-if="viewMode === 'month'">
          <div class="mb-3 flex items-center justify-between">
            <button type="button" class="text-muted-foreground hover:bg-muted hover:text-foreground flex size-7 cursor-pointer items-center justify-center rounded" @click="prevYear"><ChevronLeft class="size-4" /></button>
            <button type="button" class="hover:bg-muted hover:text-primary cursor-pointer rounded px-2 py-1 text-sm font-semibold" @click="viewMode = 'year'">{{ viewYear }} 年</button>
            <button type="button" class="text-muted-foreground hover:bg-muted hover:text-foreground flex size-7 cursor-pointer items-center justify-center rounded" @click="nextYear"><ChevronRight class="size-4" /></button>
          </div>
          <div class="grid grid-cols-3 gap-1">
            <button
              v-for="(label, i) in MONTH_NAMES"
              :key="label"
              type="button"
              :class="[
                'flex h-10 cursor-pointer items-center justify-center rounded text-sm transition-colors',
                selected && selected.year === viewYear && selected.month === (i + 1)
                  ? 'bg-primary text-primary-foreground hover:bg-primary font-semibold'
                  : 'hover:bg-accent hover:text-accent-foreground',
              ]"
              @click="pickMonth(i + 1)"
            >{{ label }}</button>
          </div>
        </template>

        <!-- YEAR -->
        <template v-else-if="viewMode === 'year'">
          <div class="mb-3 flex items-center justify-between">
            <button type="button" class="text-muted-foreground hover:bg-muted hover:text-foreground flex size-7 cursor-pointer items-center justify-center rounded" @click="prevYearGrid"><ChevronLeft class="size-4" /></button>
            <span class="text-sm font-semibold">{{ yearGridLabel }}</span>
            <button type="button" class="text-muted-foreground hover:bg-muted hover:text-foreground flex size-7 cursor-pointer items-center justify-center rounded" @click="nextYearGrid"><ChevronRight class="size-4" /></button>
          </div>
          <div class="grid grid-cols-3 gap-1">
            <button
              v-for="y in yearGrid"
              :key="y"
              type="button"
              :class="[
                'flex h-10 cursor-pointer items-center justify-center rounded text-sm transition-colors',
                selected && selected.year === y
                  ? 'bg-primary text-primary-foreground hover:bg-primary font-semibold'
                  : 'hover:bg-accent hover:text-accent-foreground',
              ]"
              @click="pickYear(y)"
            >{{ y }}</button>
          </div>
        </template>

        <div class="mt-2 flex justify-between gap-2 border-t pt-2">
          <template v-if="viewMode === 'day'">
            <button type="button" class="text-muted-foreground hover:bg-muted hover:text-primary cursor-pointer rounded px-2 py-1 text-xs" @click="pickToday">今天</button>
            <div class="flex gap-1">
              <button v-if="modelValue" type="button" class="text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer rounded px-2 py-1 text-xs" @click="clearValue">清除</button>
              <button type="button" class="text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer rounded px-2 py-1 text-xs" @click="open = false">關閉</button>
            </div>
          </template>
          <button v-else type="button" class="hover:bg-muted flex w-full cursor-pointer items-center justify-center rounded-md border px-3 py-1.5 text-xs" @click="open = false">關閉</button>
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
