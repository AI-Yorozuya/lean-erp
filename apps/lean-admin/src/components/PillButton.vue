<script setup>
// 共用膠囊鈕：訂單「訂單操作」列（收款/出貨/編輯/作廢）用。
// size sm(32px) 高度 + 膠囊(rounded-full) + 最小寬度可容五個中文字 → 短字置中、每顆一樣寬高。
// 包在 Button 外層，variant/disabled/@click/class 都往下傳；class 交給 Button 內部 cn() 合併。
import { Button } from '@/components/ui/button'

defineProps({
  variant: { type: String, default: 'default' },
  disabled: { type: Boolean, default: false },
  class: { type: null, default: '' },
})
</script>

<template>
  <Button :variant="variant" size="sm" :disabled="disabled" :class="['min-w-24 rounded-full', $props.class]">
    <slot />
  </Button>
</template>
