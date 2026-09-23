// 登入狀態（誰在操作）。只有一份，殼、守衛、登入頁都讀這裡。
// 真相在後端 session；前端這份只是快取，開站先問一次 /auth/me。
import { ref } from 'vue'
import { fetchCsrf, me, login as apiLogin, logout as apiLogout } from '@/api'

const user = ref(null) // { username, display_name } 或 null
let checked = false

export function useSession() {
  async function ensure() {
    if (checked) return !!user.value
    checked = true
    try {
      await fetchCsrf()
      user.value = await me()
    } catch {
      user.value = null
    }
    return !!user.value
  }
  async function login(username, password) {
    await fetchCsrf()
    await apiLogin(username, password)
    user.value = await me()
    checked = true
  }
  async function logout() {
    await apiLogout()
    user.value = null
  }
  return { user, ensure, login, logout }
}
