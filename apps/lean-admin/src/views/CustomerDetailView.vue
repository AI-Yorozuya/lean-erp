<script setup>
// 客戶詳細（系統總覽・頁面 customer_detail）：名稱、聯絡人；儲存、取消。
// 新增客戶也是這一頁（詳細頁負責建立、檢視、編輯）。報價紀錄與最近一張報價是反算出來的，只看。
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import PillButton from '@/components/PillButton.vue'
import LoadingState from '@/components/LoadingState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { getCustomer, createCustomer, saveCustomer, errorText } from '@/api'
import { toast } from '@/lib/toast'
import { useLeaveGuard } from '@/lib/useLeaveGuard'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.name === 'customer-new')

const c = ref(null)
const form = reactive({ name: '', contact: '' })
let snapshot = JSON.stringify(form)
const loading = ref(false)
const loadError = ref('')
const error = ref('')
const saving = ref(false)
const nameInput = ref(null)

async function load() {
  if (!['customer-new', 'customer-detail'].includes(route.name)) return
  error.value = ''
  if (isNew.value) {
    c.value = null
    Object.assign(form, { name: '', contact: '' })
  } else {
    loading.value = true
    try {
      c.value = await getCustomer(route.params.id)
      Object.assign(form, { name: c.value.name, contact: c.value.contact })
    } catch (e) {
      loadError.value = e.response?.status === 404 ? '找不到這個客戶' : errorText(e)
    } finally {
      loading.value = false
    }
  }
  snapshot = JSON.stringify(form)
}
watch(() => route.fullPath, load)
onMounted(load)

const guard = useLeaveGuard(() => JSON.stringify(form) !== snapshot)

async function save() {
  error.value = ''
  if (!form.name.trim()) {
    error.value = '名稱不能空白'
    nameInput.value?.focus()
    return
  }
  saving.value = true
  try {
    const payload = { name: form.name.trim(), contact: form.contact.trim() }
    const saved = isNew.value ? await createCustomer(payload) : await saveCustomer(c.value.id, payload)
    toast(`已儲存 ${saved.name}`, 'success')
    guard.approve()
    router.push('/customers')
  } catch (e) {
    error.value = errorText(e, '儲存失敗，稍後再試')
  } finally {
    saving.value = false
  }
}
const cellInput = 'focus:bg-muted/30 h-9 w-full bg-transparent px-3 text-sm outline-none'
</script>

<template>
  <form class="flex min-h-full flex-col" @submit.prevent="save">
    <div class="flex shrink-0 items-center gap-2">
      <Button as-child variant="outline" size="sm" class="min-w-28 shrink-0 rounded-full">
        <RouterLink to="/customers"><ArrowLeft class="size-4" /> 回上一頁</RouterLink>
      </Button>
      <div class="bg-border mx-1 h-6 w-px shrink-0"></div>
      <h1 class="truncate text-lg leading-none font-semibold tracking-tight">{{ isNew ? '新增客戶' : `客戶 ${c?.name ?? ''}` }}</h1>
      <div v-if="isNew || c" class="ml-10 flex shrink-0 items-center gap-2">
        <span class="text-muted-foreground text-sm">客戶操作：</span>
        <PillButton type="submit" :disabled="saving">儲存</PillButton>
        <Button as-child variant="outline" size="sm" class="min-w-24 rounded-full"><RouterLink to="/customers">取消</RouterLink></Button>
      </div>
    </div>

    <LoadingState v-if="loading" class="mt-5" />
    <div v-else-if="loadError" class="bg-card text-destructive mt-5 rounded-lg border p-10 text-center text-sm shadow-sm">{{ loadError }}</div>
    <div v-else class="bg-card mt-5 shrink-0 overflow-hidden rounded-lg border shadow-sm">
      <div class="border-b px-4 py-2.5 text-sm font-semibold">客戶資料</div>
      <dl class="grid grid-cols-1 text-sm sm:grid-cols-2">
        <div class="flex border-b">
          <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">名稱</dt>
          <dd class="min-w-0 flex-1">
            <input ref="nameInput" v-model="form.name" name="name" aria-label="名稱" autocomplete="organization" :aria-invalid="!!error" :class="cellInput" />
            <p v-if="error" class="text-destructive px-3 pb-1.5 text-xs" role="alert">{{ error }}</p>
          </dd>
        </div>
        <div class="flex border-b sm:border-l">
          <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">聯絡人</dt>
          <dd class="min-w-0 flex-1"><input v-model="form.contact" name="contact" aria-label="聯絡人" autocomplete="name" :class="cellInput" /></dd>
        </div>
        <div class="flex">
          <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">報價紀錄</dt>
          <dd class="flex-1 px-3 py-2 tabular-nums">{{ c ? `${c.quote_count} 筆` : '—' }}</dd>
        </div>
        <div class="flex border-t sm:border-t-0 sm:border-l">
          <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">最近一張報價</dt>
          <dd class="flex-1 px-3 py-2 tabular-nums">
            <RouterLink v-if="c?.last_quote_id" :to="`/quotations/${c.last_quote_id}`" class="hover:text-primary hover:underline">{{ c.last_quote_no }}</RouterLink>
            <span v-else>—</span>
          </dd>
        </div>
      </dl>
    </div>

    <ConfirmDialog :open="guard.leaveOpen.value" title="還沒存，確定要離開？" description="這一頁改的東西還沒存，離開就不見了。"
      confirm-text="離開" cancel-text="留下來" destructive @confirm="guard.answer(true)" @cancel="guard.answer(false)" />
  </form>
</template>
