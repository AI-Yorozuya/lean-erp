// 最小的 API 包裝：建一個 axios instance，baseURL 設成 /api/v1。
// 搭配 vite.config.js 的 proxy，/api 會被轉到後端 :8000。
import axios from 'axios'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// 對應後端 GET /api/v1/health → { status: "ok" }
export function getHealth() {
  return http.get('/health').then((res) => res.data)
}

// ── 背景任務（progress）─────────────────────────────────────
// GET /api/v1/progress → 所有背景任務清單（最新在前）。有 RUNNING 就每 3 秒輪詢。
export function listJobs() {
  return http.get('/progress').then((res) => res.data)
}

// POST /api/v1/progress/demo → 派一個示範任務，回 job 資料
export function startDemoJob() {
  return http.post('/progress/demo').then((res) => res.data)
}

// GET /api/v1/progress/{id} → 查單一任務目前進度
export function getJob(id) {
  return http.get(`/progress/${id}`).then((res) => res.data)
}

export default http
