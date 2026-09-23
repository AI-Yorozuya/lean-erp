<script setup>
// 商品詳細（系統總覽・頁面 product_detail，規格 sp_product_save）：型號、名稱、單價；儲存、取消。
// 失敗：型號、名稱空白或單價不大於 0 不能存，型號不能跟別的商品重複——畫面提示、資料不變。
// 成功：留在商品詳細頁，看到新值。新增商品也是這一頁。
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import PillButton from '@/components/PillButton.vue'
import LoadingState from '@/components/LoadingState.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { getProduct, createProduct, saveProduct, errorText } from '@/api'
import { toast } from '@/lib/toast'
import { useLeaveGuard } from '@/lib/useLeaveGuard'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.name === 'product-new')

const p = ref(null)
const form = reactive({ model: '', name: '', price: '' })
const snapshot = ref(JSON.stringify(form))
const loading = ref(false)
const loadError = ref('')
const errors = reactive({ model: '', name: '', price: '', server: '' })
const saving = ref(false)
const refs = { model: ref(null), name: ref(null), price: ref(null) }
const [modelInput, nameInput, priceInput] = [refs.model, refs.name, refs.price]

async function load() {
  if (!['product-new', 'product-detail'].includes(route.name)) return
  Object.assign(errors, { model: '', name: '', price: '', server: '' })
  if (isNew.value) {
    p.value = null
    Object.assign(form, { model: '', name: '', price: '' })
  } else if (p.value?.id !== Number(route.params.id)) {
    loading.value = true
    try {
      p.value = await getProduct(route.params.id)
      Object.assign(form, { model: p.value.model, name: p.value.name, price: p.value.price })
    } catch (e) {
      loadError.value = e.response?.status === 404 ? '找不到這個商品' : errorText(e)
    } finally {
      loading.value = false
    }
  }
  snapshot.value = JSON.stringify(form)
}
watch(() => route.fullPath, load)
onMounted(load)

const guard = useLeaveGuard(() => JSON.stringify(form) !== snapshot.value)

async function save() {
  errors.model = form.model.trim() ? '' : '型號不能空白'
  errors.name = form.name.trim() ? '' : '名稱不能空白'
  errors.price = Number(form.price) > 0 ? '' : '單價要大於 0'
  errors.server = ''
  const first = ['model', 'name', 'price'].find((k) => errors[k])
  if (first) { refs[first].value?.focus(); return }
  saving.value = true
  try {
    const payload = { model: form.model.trim(), name: form.name.trim(), price: Number(form.price) }
    const saved = isNew.value ? await createProduct(payload) : await saveProduct(p.value.id, payload)
    p.value = saved
    Object.assign(form, { model: saved.model, name: saved.name, price: saved.price })
    snapshot.value = JSON.stringify(form)
    toast(`已儲存 ${saved.model}`, 'success')
    if (isNew.value) { guard.approve(); router.replace(`/products/${saved.id}`) }
  } catch (e) {
    const msg = errorText(e, '儲存失敗，稍後再試')
    if (msg.includes('型號')) errors.model = msg
    else errors.server = msg
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
        <RouterLink to="/products"><ArrowLeft class="size-4" /> 回上一頁</RouterLink>
      </Button>
      <div class="bg-border mx-1 h-6 w-px shrink-0"></div>
      <h1 class="truncate text-lg leading-none font-semibold tracking-tight">{{ isNew ? '新增商品' : `商品 ${p?.model ?? ''}` }}</h1>
      <div v-if="isNew || p" class="ml-10 flex shrink-0 items-center gap-2">
        <span class="text-muted-foreground text-sm">商品操作：</span>
        <PillButton type="submit" :disabled="saving">儲存</PillButton>
        <Button as-child variant="outline" size="sm" class="min-w-24 rounded-full"><RouterLink to="/products">取消</RouterLink></Button>
      </div>
      <span v-if="errors.server" class="text-destructive ml-4 text-sm" role="alert">{{ errors.server }}</span>
    </div>

    <LoadingState v-if="loading" class="mt-5" />
    <div v-else-if="loadError" class="bg-card text-destructive mt-5 rounded-lg border p-10 text-center text-sm shadow-sm">{{ loadError }}</div>
    <div v-else class="bg-card mt-5 shrink-0 overflow-hidden rounded-lg border shadow-sm">
      <div class="border-b px-4 py-2.5 text-sm font-semibold">商品資料</div>
      <dl class="grid grid-cols-1 text-sm sm:grid-cols-2">
        <div class="flex border-b">
          <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">型號</dt>
          <dd class="min-w-0 flex-1">
            <input ref="modelInput" v-model="form.model" name="model" aria-label="型號" :aria-invalid="!!errors.model" :class="cellInput" />
            <p v-if="errors.model" class="text-destructive px-3 pb-1.5 text-xs" role="alert">{{ errors.model }}</p>
          </dd>
        </div>
        <div class="flex border-b sm:border-l">
          <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">單價</dt>
          <dd class="min-w-0 flex-1">
            <input ref="priceInput" v-model="form.price" name="price" aria-label="單價" inputmode="numeric" :aria-invalid="!!errors.price" :class="[cellInput, 'tabular-nums']" />
            <p v-if="errors.price" class="text-destructive px-3 pb-1.5 text-xs" role="alert">{{ errors.price }}</p>
          </dd>
        </div>
        <div class="flex sm:col-span-2">
          <dt class="text-muted-foreground bg-muted/40 w-24 shrink-0 border-r px-3 py-2">名稱</dt>
          <dd class="min-w-0 flex-1">
            <input ref="nameInput" v-model="form.name" name="name" aria-label="名稱" :aria-invalid="!!errors.name" :class="cellInput" />
            <p v-if="errors.name" class="text-destructive px-3 pb-1.5 text-xs" role="alert">{{ errors.name }}</p>
          </dd>
        </div>
      </dl>
    </div>

    <ConfirmDialog :open="guard.leaveOpen.value" title="還沒存，確定要離開？" description="這一頁改的東西還沒存，離開就不見了。"
      confirm-text="離開" cancel-text="留下來" destructive @confirm="guard.answer(true)" @cancel="guard.answer(false)" />
  </form>
</template>
