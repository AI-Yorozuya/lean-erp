<script setup>
// toast 的畫面層（狀態在 src/lib/toast.js）。掛在 AppShell，一個 app 一份。
import { X } from '@lucide/vue'
import { toasts, dismiss } from '@/lib/toast'
</script>

<template>
  <div class="pointer-events-none fixed right-4 top-16 z-[100] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
    <transition-group
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="translate-y-1 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        :class="[
          'pointer-events-auto flex items-start gap-2 rounded-md border px-3 py-2.5 text-sm shadow-lg',
          t.kind === 'error'
            ? 'border-destructive/30 bg-destructive text-destructive-foreground'
            : 'border-border bg-foreground text-background',
        ]"
      >
        <span class="min-w-0 flex-1">{{ t.message }}</span>
        <button type="button" class="shrink-0 cursor-pointer opacity-70 hover:opacity-100" title="關閉" @click="dismiss(t.id)">
          <X class="size-4" />
        </button>
      </div>
    </transition-group>
  </div>
</template>
