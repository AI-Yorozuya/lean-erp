// 後台路由。報價單詳細頁一個檔管開新單／檢視／編輯三個模式（照 ns/top：同一個骨架，只換可編輯的格子）。
import { createRouter, createWebHistory } from 'vue-router'
import { useSession } from '@/session'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/', redirect: '/quotations' },
  { path: '/quotations', name: 'quotations', component: () => import('@/views/QuotationListView.vue') },
  { path: '/quotations/new', name: 'quotation-new', component: () => import('@/views/QuotationDetailView.vue') },
  { path: '/quotations/:id', name: 'quotation-detail', component: () => import('@/views/QuotationDetailView.vue') },
  { path: '/quotations/:id/edit', name: 'quotation-edit', component: () => import('@/views/QuotationDetailView.vue') },
  { path: '/orders', name: 'orders', component: () => import('@/views/OrderListView.vue') },
  { path: '/orders/:id', name: 'order-detail', component: () => import('@/views/OrderDetailView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 登入守衛：除了標 public 的頁，沒登入就轉去 /login，登入後回原頁。
router.beforeEach(async (to) => {
  if (to.meta.public) return true
  if (!(await useSession().ensure())) return { name: 'login', query: { next: to.fullPath } }
  return true
})

export default router
