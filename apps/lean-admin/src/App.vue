<script setup>
// 最外層：登入頁不套殼；其他頁套應用外殼（sidebar + 頂部 bar），內容交給路由。
import { useRoute } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
const route = useRoute()
</script>

<template>
  <router-view v-if="route.meta.public" />
  <AppShell v-else>
    <router-view />
  </AppShell>
</template>
