<script setup>
// 種子首頁：骨架跑起來的證據頁。三張表的頁面照 intents/ 逐塊長出來後，這頁會被列表頁取代。
import { ref, onMounted } from 'vue'
import api from '@/api'

const health = ref(null)
onMounted(async () => {
  try { health.value = (await api.get('/health')).data } catch { health.value = { status: 'down' } }
})
</script>

<template>
  <div class="p-8">
    <h1 class="text-2xl font-semibold">lean-erp</h1>
    <p class="mt-2 text-muted-foreground">報價成交切片：客戶 → 報價單 → 訂單。</p>
    <p class="mt-6 text-sm">
      後端連線：<span class="font-mono">{{ health?.status ?? '…' }}</span>
    </p>
    <p class="mt-8 text-sm text-muted-foreground">
      這個系統的判斷寫在 <span class="font-mono">intents/</span>：先看架構圖，再看功能規格書。
    </p>
  </div>
</template>
