// 後台路由。詳細頁一個檔管新增／檢視／編輯（照 ns/top：同一個骨架，只換可編輯的格子）。
import { createRouter, createWebHistory } from 'vue-router'
import { useSession } from '@/session'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/', redirect: '/quotations' },
  // 銷售管理：客戶、商品、報價單（系統總覽的頁面表）
  { path: '/customers', name: 'customers', component: () => import('@/views/CustomerListView.vue') },
  { path: '/customers/new', name: 'customer-new', component: () => import('@/views/CustomerDetailView.vue') },
  { path: '/customers/:id', name: 'customer-detail', component: () => import('@/views/CustomerDetailView.vue') },
  { path: '/products', name: 'products', component: () => import('@/views/ProductListView.vue') },
  { path: '/products/new', name: 'product-new', component: () => import('@/views/ProductDetailView.vue') },
  { path: '/products/:id', name: 'product-detail', component: () => import('@/views/ProductDetailView.vue') },
  { path: '/quotations', name: 'quotations', component: () => import('@/views/QuotationListView.vue') },
  { path: '/quotations/new', name: 'quotation-new', component: () => import('@/views/QuotationDetailView.vue') },
  { path: '/quotations/:id', name: 'quotation-detail', component: () => import('@/views/QuotationDetailView.vue') },
  { path: '/quotations/:id/edit', name: 'quotation-edit', component: () => import('@/views/QuotationDetailView.vue') },
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
