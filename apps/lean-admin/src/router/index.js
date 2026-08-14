// 後台路由。
//
// 教學重點（怎麼加一頁）：
//   1) 在 src/views/ 新增一個 .vue（例如 UsersView.vue）。
//   2) 在下面 routes 陣列加一筆 { path: '/users', component: () => import('@/views/UsersView.vue') }。
//      用 () => import(...) 是 lazy load：進到該頁才下載，首頁更快。
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
  // 新頁面路由加在這（客戶 / 報價單 / 訂單照 intents/ 逐塊長出來）
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ──────────────────────────────────────────────────────────────
// AUTH 接縫（目前刻意留空）
// 後台是最需要登入/權限的地方。之後在這裡加一個 beforeEach 守衛：
//   - 檢查登入狀態（token / session），未登入就 router.push('/login')
//   - 後端對應的 auth 接縫在 lean-backend 的 core/api.py（NinjaAPI auth=...）
// 例：
//   router.beforeEach((to) => {
//     const isLoggedIn = /* 讀 token */ false
//     if (!isLoggedIn && to.name !== 'login') return { name: 'login' }
//   })
// ──────────────────────────────────────────────────────────────

export default router
