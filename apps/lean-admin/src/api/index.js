// 最小的 API 包裝：建一個 axios instance，baseURL 設成 /api/v1。
// 搭配 vite.config.js 的 proxy，/api 會被轉到後端 :8000。
//
// 登入是 session（cookie）：開站先 GET /auth/csrf 拿 csrftoken，之後每個 POST／PUT 帶 X-CSRFToken
// （axios 認得 xsrf 那兩個設定就會自己帶）。後端回 401＝沒登入，統一在這裡轉去 /login。
import axios from 'axios'
import router from '@/router'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && router.currentRoute.value.name !== 'login') {
      router.push({ name: 'login', query: { next: router.currentRoute.value.fullPath } })
    }
    return Promise.reject(err)
  },
)

const data = (p) => p.then((res) => res.data)

// 後端錯誤訊息（HttpError 的 detail）拿出來給人看；沒有就給一句通用的
export const errorText = (e, fallback = '操作失敗，稍後再試') => e?.response?.data?.detail || fallback

export const getHealth = () => data(http.get('/health'))

// ── 登入 ──
export const fetchCsrf = () => data(http.get('/auth/csrf'))
export const login = (username, password) => data(http.post('/auth/login', { username, password }))
export const logout = () => data(http.post('/auth/logout'))
export const me = () => data(http.get('/auth/me'))

// ── 客戶、商品（挑選框用：{page,pageSize,search} → {items,count}）──
const pageParams = ({ page = 1, pageSize = 8, search = '' } = {}) => ({ page, page_size: pageSize, search })
export const listCustomers = (opts) => data(http.get('/customers', { params: pageParams(opts) }))
export const createCustomer = (payload) => data(http.post('/customers', payload))
export const listProducts = (opts) => data(http.get('/products', { params: pageParams(opts) }))

// ── 報價單 ──
export const listQuotations = ({ status = '', search = '', page = 1, pageSize = 20 } = {}) =>
  data(http.get('/quotations', { params: { status, search, page, page_size: pageSize } }))
export const getQuotation = (id) => data(http.get(`/quotations/${id}`))
export const createQuotation = (payload) => data(http.post('/quotations', payload))
export const updateQuotation = (id, payload) => data(http.put(`/quotations/${id}`, payload))
// action：send／recall／win／lose／reopen
export const quotationAction = (id, action) => data(http.post(`/quotations/${id}/${action}`))
export const quotationPdfUrl = (id) => `/api/v1/quotations/${id}/pdf`

// ── 訂單 ──
export const listOrders = ({ status = '', search = '', page = 1, pageSize = 20 } = {}) =>
  data(http.get('/orders', { params: { status, search, page, page_size: pageSize } }))
export const getOrder = (id) => data(http.get(`/orders/${id}`))
export const convertToOrder = (quotationId) => data(http.post('/orders', { quotation_id: quotationId }))
// action：start／finish／back／reopen／void
export const orderAction = (id, action) => data(http.post(`/orders/${id}/${action}`))

export default http
