<script setup>
// 應用外殼（app shell）：常駐的左側 sidebar + 頂部 bar + 中間內容區。
// 配色走白底極簡（參考 ERPNext desk 側欄）；結構（可收合 + 多層選單）參考 top-admin。
// 所有頁面都長在這個殼裡（見 App.vue 把 <router-view/> 塞進 <slot/>）。
//
// 教學重點：
//   - 「版面」與「頁面」分離：殼負責導覽/框架，頁面只管自己的內容。
//   - nav 支援兩種：單一項（有 to）與群組（有 children）。加頁往這個陣列加一筆。
//   - active 用 derive（讀 route，不用 watch）；含 active 子項的群組自動展開。
//   - 可收合（w-56 完整 ⇄ w-16 icon-only），狀態存 localStorage、小螢幕自動收。
import { ref, watch, onBeforeMount, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
// 選單 icon 一律取「同一套 lucide、視覺重量相近的實心輪廓物件」——參 top-admin 的
// constants/icons.js（避免混入 Activity 那種稀疏脈衝線，破壞整體一致性）。
import { CalendarCheck, Users, ChevronDown, ChevronsLeft, ChevronsRight, User, FileText } from '@lucide/vue'
import { getHealth } from '@/api'
import HealthBadge from '@/components/HealthBadge.vue'
import Toaster from '@/components/Toaster.vue'
// 品牌標：忍者熊頭徽章（換店名時改下面 template 的字；圖要換就換這個 import）。
import bearBadge from '@/assets/bearhead_badge.png'

// 導覽：單一項 { to, label, icon }；群組 { label, icon, children:[{ to, label }] }。
// 標籤設計上限：中文 6 字（側欄寬度就是抓這個預算 + logo 一起定的）。
// 三張表的頁面照 intents/ 逐塊長出來後掛在這。
const nav = [
  { to: '/', label: '首頁', icon: Users },
  { to: '/quotations', label: '報價單', icon: FileText },
]

const route = useRoute()
// active 用前綴比對：子路由（如 /orders/21、/orders/21/edit）也讓父項（訂單）保持 active。
const isItemActive = (to) => route.path === to || route.path.startsWith(to + '/')
const isGroupActive = (item) => item.children.some((c) => isItemActive(c.to))

// ── 群組展開狀態 ──
// 開合只認 openGroups 這一個真相（不再用「active 子項」臨時算開，那會讓群組一離開就自動收、忽開忽關）。
const openGroups = ref(new Set())
const isGroupOpen = (item) => openGroups.value.has(item.label)
function toggleGroup(item) {
  // 收合狀態下點群組 → 先把側欄展開，再打開該群組。
  if (!expanded.value) {
    expanded.value = true
    localStorage.setItem(STORAGE_KEY, 'true')
    openGroups.value.add(item.label)
    return
  }
  if (openGroups.value.has(item.label)) openGroups.value.delete(item.label)
  else openGroups.value.add(item.label)
}

// 導到某群組的子項時，自動把該群組打開並「記住」——之後離開（例如點背景任務）不會自動關，
// 要收起就自己點群組標題。這樣開合才一致（immediate：初次載入落在子項也會展開）。
watch(
  () => route.path,
  () => {
    for (const item of nav) {
      if (item.children && isGroupActive(item)) openGroups.value.add(item.label)
    }
  },
  { immediate: true },
)

// ── 收合狀態（localStorage 持久化 + 小螢幕自動收）──
const expanded = ref(true)
const STORAGE_KEY = 'leanSidebarExpanded'
const MOBILE_BP = 1024
const isMobile = () => typeof window !== 'undefined' && window.innerWidth < MOBILE_BP

onBeforeMount(() => {
  if (isMobile()) {
    expanded.value = false
    return
  }
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored !== null) expanded.value = stored === 'true'
})

function toggle() {
  expanded.value = !expanded.value
  localStorage.setItem(STORAGE_KEY, String(expanded.value))
}

function handleResize() {
  // 小螢幕自動收；回到大螢幕要把使用者原本的偏好放回來——不然載入途中視窗短暫變窄
  // （像預覽面板拉開的那一瞬間）就會把側欄永久收起，而且還蓋掉 localStorage 的選擇。
  if (isMobile()) {
    if (expanded.value) expanded.value = false
  } else if (localStorage.getItem(STORAGE_KEY) !== 'false') {
    expanded.value = true
  }
}

// ── 後端連線狀態（殼掛載時打一次 health）──
const status = ref('checking') // checking | ok | error

// ── 使用者選單（avatar；目前無 auth，是佔位＋之後接使用者的接縫）──
const userMenuOpen = ref(false)
const userMenuRef = ref(null)
function onClickOutside(e) {
  if (userMenuRef.value && !userMenuRef.value.contains(e.target)) userMenuOpen.value = false
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  document.addEventListener('click', onClickOutside)
  try {
    const data = await getHealth()
    status.value = data.status === 'ok' ? 'ok' : 'error'
  } catch (e) {
    console.error('health check failed:', e)
    status.value = 'error'
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('click', onClickOutside)
})
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden">
    <!-- ── 左側 sidebar（白底極簡，可收合）───────────────── -->
    <aside
      class="flex h-full flex-col overflow-hidden border-r border-border bg-card transition-[width] duration-200"
      :class="expanded ? 'w-44' : 'w-16'"
    >
      <!-- 品牌列（h-14 對齊頂 bar；整塊是連結，點了回站台入口 = 會員頁）。
           px-5 讓熊頭 logo 的左緣＝下方選單 icon 的左緣（nav 的 p-2 + px-3 = 20px），
           整條側欄共用同一條「icon 軌」。寬度 w-44 是抓「6 字標籤 + 品牌字」的下限一起定的。 -->
      <button
        type="button"
        title="lean-erp · 報價成交"
        class="flex h-14 shrink-0 cursor-pointer items-center gap-3 overflow-hidden border-b border-border text-left transition-opacity hover:opacity-70"
        :class="expanded ? 'justify-start px-5' : 'justify-center'"
        @click="$router.push('/')"
      >
        <img :src="bearBadge" alt="lean-erp" class="size-8 shrink-0" />
        <span v-show="expanded" class="whitespace-nowrap text-[15px] font-semibold text-foreground">lean-erp</span>
      </button>

      <!-- Menu -->
      <nav class="flex flex-1 flex-col gap-0.5 overflow-x-hidden overflow-y-auto p-2">
        <template v-for="item in nav" :key="item.label">
          <!-- 單一項 -->
          <RouterLink v-if="item.to" v-slot="{ isActive }" :to="item.to" custom>
            <button
              :title="item.label"
              :class="[
                'flex w-full items-center rounded-md text-sm transition-colors',
                expanded ? 'gap-3 px-3 py-2' : 'justify-center px-0 py-2.5',
                isItemActive(item.to)
                  ? 'relative bg-muted font-medium text-foreground before:absolute before:top-1/2 before:left-0 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-full before:bg-primary'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              ]"
              @click="$router.push(item.to)"
            >
              <component :is="item.icon" class="size-[18px] shrink-0" />
              <span v-show="expanded" class="whitespace-nowrap">{{ item.label }}</span>
            </button>
          </RouterLink>

          <!-- 群組（父 + 子）-->
          <template v-else>
            <button
              :title="item.label"
              :class="[
                'flex w-full items-center rounded-md text-sm transition-colors',
                expanded ? 'gap-3 px-3 py-2' : 'justify-center px-0 py-2.5',
                isGroupActive(item)
                  ? 'font-medium text-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              ]"
              @click="toggleGroup(item)"
            >
              <component :is="item.icon" class="size-[18px] shrink-0" />
              <template v-if="expanded">
                <span class="flex-1 whitespace-nowrap text-left">{{ item.label }}</span>
                <ChevronDown class="size-4 transition-transform duration-200" :class="isGroupOpen(item) ? 'rotate-180' : ''" />
              </template>
            </button>

            <!-- 子項（只在展開 + 群組打開時顯示）-->
            <div v-show="expanded && isGroupOpen(item)" class="mt-0.5 flex flex-col gap-0.5">
              <RouterLink v-for="child in item.children" :key="child.to" :to="child.to" custom>
                <button
                  :class="[
                    'flex w-full items-center rounded-md py-2 pl-11 pr-3 text-left text-sm transition-colors',
                    isItemActive(child.to)
                      ? 'relative bg-muted font-medium text-foreground before:absolute before:top-1/2 before:left-8 before:h-4 before:w-[3px] before:-translate-y-1/2 before:rounded-full before:bg-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  ]"
                  @click="$router.push(child.to)"
                >
                  <span class="whitespace-nowrap">{{ child.label }}</span>
                </button>
              </RouterLink>
            </div>
          </template>
        </template>
      </nav>

      <div v-show="expanded" class="overflow-hidden p-4 text-xs whitespace-nowrap text-muted-foreground">lean-erp · 報價成交</div>
    </aside>

    <!-- ── 右側：頂部 bar + 內容 ─────────────────────── -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <header class="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card px-6">
        <button
          type="button"
          :title="expanded ? '收合側邊欄' : '展開側邊欄'"
          class="-ml-2 inline-flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-muted hover:text-foreground active:scale-95"
          @click="toggle"
        >
          <ChevronsLeft v-if="expanded" class="size-5" />
          <ChevronsRight v-else class="size-5" />
        </button>

        <!-- 右：後端連線指示 + 使用者 avatar（avatar 是 auth 之後接使用者選單的接縫）-->
        <div class="flex items-center gap-4">
          <HealthBadge :status="status" />
          <div ref="userMenuRef" class="relative">
            <button
              type="button"
              title="訪客（尚未登入）"
              class="inline-flex size-9 items-center justify-center rounded-full border border-border bg-card text-foreground shadow-sm transition-all hover:bg-muted hover:text-foreground active:scale-95"
              :class="userMenuOpen ? 'ring-2 ring-ring ring-offset-2' : ''"
              @click="userMenuOpen = !userMenuOpen"
            >
              <User class="size-4" />
            </button>
            <transition
              enter-active-class="transition duration-100 ease-out"
              enter-from-class="-translate-y-1 scale-95 opacity-0"
              enter-to-class="translate-y-0 scale-100 opacity-100"
              leave-active-class="transition duration-75 ease-in"
              leave-to-class="-translate-y-1 scale-95 opacity-0"
            >
              <div v-if="userMenuOpen" class="absolute top-full right-0 z-50 mt-2 min-w-44 origin-top-right rounded-md border border-border bg-card py-1 shadow-lg">
                <div class="border-b border-border px-4 py-2 text-sm font-medium text-foreground">訪客</div>
                <div class="px-4 py-2 text-xs text-muted-foreground">尚未登入 · auth 之後在這接使用者選單</div>
              </div>
            </transition>
          </div>
        </div>
      </header>

      <main class="main-content min-w-0 flex-1 overflow-auto p-5">
        <slot />
      </main>
    </div>

    <!-- 頁面級錯誤/提示（浮出，不塞頁面頂端）-->
    <Toaster />
  </div>
</template>

<style scoped>
/* 內容區底色（暖奶油紙，比卡片深一點讓卡片浮起來）+ 暖捲軸。 */
.main-content {
  background-color: #fbfcfe;
}
.main-content::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}
.main-content::-webkit-scrollbar-thumb {
  background-color: rgb(15 23 42 / 0.6);
  border-radius: 9999px;
  border: 0.5px solid transparent;
  background-clip: padding-box;
}
.main-content::-webkit-scrollbar-thumb:hover {
  background-color: rgb(15 23 42 / 0.8);
}
nav::-webkit-scrollbar {
  width: 4px;
}
nav::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 2px;
}
</style>
