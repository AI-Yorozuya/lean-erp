<script setup>
// 登入頁：帳號、密碼、一顆按鈕。成功後回原本要去的頁（?next=），沒有就回首頁。
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSession } from '@/session'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const route = useRoute()
const router = useRouter()
const session = useSession()

const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await session.login(username.value, password.value)
    router.replace(typeof route.query.next === 'string' ? route.query.next : '/')
  } catch (e) {
    error.value = e.response?.status === 401 ? '帳號或密碼不對' : '連不上後端，稍後再試'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-muted/40 p-6">
    <Card class="w-full max-w-sm">
      <CardHeader>
        <CardTitle>登入 lean-erp</CardTitle>
        <CardDescription>本機開發預設帳號 dev / dev1234</CardDescription>
      </CardHeader>
      <CardContent>
        <form class="flex flex-col gap-4" @submit.prevent="submit">
          <div class="flex flex-col gap-2">
            <Label for="username">帳號</Label>
            <Input id="username" v-model="username" autocomplete="username" required autofocus />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="password">密碼</Label>
            <Input id="password" v-model="password" type="password" autocomplete="current-password" required />
          </div>
          <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
          <Button type="submit" :disabled="busy">{{ busy ? '登入中…' : '登入' }}</Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
