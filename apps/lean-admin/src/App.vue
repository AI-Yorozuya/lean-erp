<script setup>
// 最外層：套上應用外殼（sidebar + 頂部 bar），內容交給路由。
import AppShell from '@/components/layout/AppShell.vue'
</script>

<template>
  <AppShell>
    <router-view />
  </AppShell>
</template>
