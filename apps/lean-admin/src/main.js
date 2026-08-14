// Vue 應用程式進入點。
// 教學版精簡：有 router（方便之後加頁），但沒有 pinia / i18n。
import './assets/index.css' // Tailwind + shadcn 設計 token（全站樣式基底）
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

createApp(App).use(router).mount('#app')
