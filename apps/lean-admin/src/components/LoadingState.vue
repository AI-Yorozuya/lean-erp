<script setup>
// 有質感的載入狀態：一圈細環繞著品牌熊頭轉，熊頭輕輕呼吸（pulse）。
// 用在「整頁/整區在等資料」的地方：<LoadingState />（可填滿父容器高度並置中）。
import bearBadge from '@/assets/bearhead_badge.png'

defineProps({
  text: { type: String, default: '載入中…' },
})
</script>

<template>
  <div class="flex min-h-40 flex-1 flex-col items-center justify-center gap-4">
    <div class="relative flex size-16 items-center justify-center">
      <!-- 細環：透明底、頂端一段主色，轉起來就是 spinner -->
      <div class="border-muted border-t-primary absolute inset-0 animate-spin rounded-full border-2"></div>
      <img :src="bearBadge" alt="" class="size-9 animate-pulse" />
    </div>
    <p class="text-muted-foreground text-sm">{{ text }}</p>
  </div>
</template>
