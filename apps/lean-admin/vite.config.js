import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // tailwindcss()：Tailwind v4 的官方 Vite plugin（v4 不需要 tailwind.config.js /
  // postcss.config.js，主題 token 直接寫在 src/assets/index.css 的 @theme 裡）。
  plugins: [vue(), tailwindcss()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    // 後台用 5174。
    port: 5174,
    // 把打到 /api 的請求，dev 時轉給後端的 :8000。
    // 好處：前端程式碼一律用相對路徑 /api/...，不用管 CORS、也不用寫死後端網址。
    proxy: {
      '/api': {
        // 容器內跑（docker compose）時由 VITE_API_PROXY_TARGET 指到 compose 內網的 backend；
        // host 上直接跑則 fallback localhost。兩種起法共用同一份 config。
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
