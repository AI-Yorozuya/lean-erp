<script setup>
// 數量輸入：左右各一個加減鈕（[−] 值 [+]），中間可直接打字。跨瀏覽器一致、好按。
import { computed } from 'vue'
import { Minus, Plus } from '@lucide/vue'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  min: { type: Number, default: 0 },
  max: { type: Number, default: Infinity },
  step: { type: Number, default: 1 },
  disabled: { type: Boolean, default: false },
  width: { type: String, default: '7.5rem' },
})
const emit = defineEmits(['update:modelValue'])

const numVal = computed(() => {
  const v = Number(props.modelValue)
  return isNaN(v) ? 0 : v
})
const canDec = computed(() => !props.disabled && numVal.value > props.min)
const canInc = computed(() => !props.disabled && numVal.value < props.max)

function setValue(v) {
  let n = Number(v)
  if (isNaN(n)) n = 0
  n = Math.max(props.min, Math.min(props.max, n))
  emit('update:modelValue', n)
}
function increase() { if (canInc.value) setValue(numVal.value + props.step) }
function decrease() { if (canDec.value) setValue(numVal.value - props.step) }
function onInput(e) {
  const v = e.target.value
  if (v === '' || v === null) { emit('update:modelValue', null); return }
  setValue(v)
}
</script>

<template>
  <div
    class="border-input bg-background focus-within:border-ring focus-within:ring-ring/50 inline-flex h-9 items-center overflow-hidden rounded-md border focus-within:ring-[3px]"
    :class="disabled && 'bg-muted cursor-not-allowed opacity-60'"
    :style="{ width }"
  >
    <button
      type="button" tabindex="-1" :disabled="!canDec"
      class="text-muted-foreground hover:bg-muted hover:text-foreground flex h-full w-8 shrink-0 cursor-pointer items-center justify-center border-r disabled:cursor-not-allowed disabled:opacity-40"
      @click="decrease"
    >
      <Minus class="size-3.5" />
    </button>
    <input
      type="number"
      :value="modelValue ?? ''"
      :disabled="disabled"
      :min="min"
      :max="max"
      :step="step"
      class="h-full w-full min-w-0 appearance-none border-0 bg-transparent text-center text-sm outline-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
      @input="onInput"
    />
    <button
      type="button" tabindex="-1" :disabled="!canInc"
      class="text-muted-foreground hover:bg-muted hover:text-foreground flex h-full w-8 shrink-0 cursor-pointer items-center justify-center border-l disabled:cursor-not-allowed disabled:opacity-40"
      @click="increase"
    >
      <Plus class="size-3.5" />
    </button>
  </div>
</template>
