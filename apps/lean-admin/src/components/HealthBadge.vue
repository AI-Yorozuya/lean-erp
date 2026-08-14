<script setup>
// 可重用的小元件：顯示後端連線狀態。
// 教學重點：用 defineProps 接收外部傳進來的資料；元件只管「怎麼顯示」。
defineProps({
  status: {
    type: String,
    default: 'checking', // checking | ok | error
  },
})
</script>

<template>
  <div class="flex items-center gap-2 text-sm">
    <span
      :class="[
        'inline-block size-2 rounded-full',
        status === 'ok' ? 'bg-green-500' : status === 'error' ? 'bg-destructive' : 'bg-muted-foreground animate-pulse',
      ]"
    />
    <span class="text-muted-foreground">
      <template v-if="status === 'ok'">後端連線正常</template>
      <template v-else-if="status === 'error'">後端連線失敗</template>
      <template v-else>檢查連線中…</template>
    </span>
  </div>
</template>
