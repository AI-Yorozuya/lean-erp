// 後台路由。詳細頁一個檔管新增／檢視／編輯（照 ns/top：同一個骨架，只換可編輯的格子）。
import { createRouter, createWebHistory } from 'vue-router'
import { useSession } from '@/session'

const SALES = { roles: ['salesperson'] }   // 銷售管理：業務
const BOSS = { roles: ['boss'] }           // 報表分析：老闆

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/', name: 'home', component: { render: () => null } },   // 守衛依角色送去首頁
  // 銷售管理：客戶、商品、報價單
  { path: '/customers', name: 'customers', component: () => import('@/views/CustomerListView.vue'), meta: SALES },
  { path: '/customers/new', name: 'customer-new', component: () => import('@/views/CustomerDetailView.vue'), meta: SALES },
  { path: '/customers/:id', name: 'customer-detail', component: () => import('@/views/CustomerDetailView.vue'), meta: SALES },
  { path: '/products', name: 'products', component: () => import('@/views/ProductListView.vue'), meta: SALES },
  { path: '/products/new', name: 'product-new', component: () => import('@/views/ProductDetailView.vue'), meta: SALES },
  { path: '/products/:id', name: 'product-detail', component: () => import('@/views/ProductDetailView.vue'), meta: SALES },
  { path: '/quotations', name: 'quotations', component: () => import('@/views/QuotationListView.vue'), meta: SALES },
  { path: '/quotations/new', name: 'quotation-new', component: () => import('@/views/QuotationDetailView.vue'), meta: SALES },
  { path: '/quotations/:id', name: 'quotation-detail', component: () => import('@/views/QuotationDetailView.vue'), meta: SALES },
  { path: '/quotations/:id/edit', name: 'quotation-edit', component: () => import('@/views/QuotationDetailView.vue'), meta: SALES },
  // 報表分析：業績
  { path: '/reports/stats', name: 'stats', component: () => import('@/views/StatsReportView.vue'), meta: BOSS },
]

// 各角色登入後的首頁
export const HOME = { salesperson: '/quotations', boss: '/reports/stats' }

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 登入守衛：除了標 public 的頁，沒登入就轉去 /login，登入後回原頁。
router.beforeEach(async (to) => {
  if (to.meta.public) return true
  const session = useSession()
  if (!(await session.ensure())) return { name: 'login', query: { next: to.fullPath } }
  const home = HOME[session.user.value.role] || '/login'
  if (to.name === 'home') return home
  if (to.meta.roles && !to.meta.roles.includes(session.user.value.role)) return home   // 進錯模組：回自己的首頁
  return true
})

export default router
