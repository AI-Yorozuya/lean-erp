<script setup>
// 確認對話框（收回、作廢、離開未存這種收不回來的動作用）。不用瀏覽器原生 confirm。
// 注意：要蓋在別的對話框上面時，這個元件在 template 裡要寫在那個對話框「後面」（reka-ui 依 template 順序疊）。
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'

defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  confirmText: { type: String, default: '確定' },
  cancelText: { type: String, default: '取消' },
  destructive: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open', 'confirm', 'cancel'])

function cancel() {
  emit('cancel')
  emit('update:open', false)
}
</script>

<template>
  <Dialog :open="open" @update:open="(v) => (v ? emit('update:open', v) : cancel())">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription v-if="description">{{ description }}</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="outline" @click="cancel">{{ cancelText }}</Button>
        <Button :variant="destructive ? 'destructive' : 'default'" :disabled="busy" @click="emit('confirm')">{{ confirmText }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
