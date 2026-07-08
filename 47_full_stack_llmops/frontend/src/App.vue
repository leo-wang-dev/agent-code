<template>
  <div class="h-full flex">
    <!-- 侧边导航：按角色差异化（文章一、用户角色和对应视图） -->
    <aside v-if="auth.isLoggedIn" class="w-52 bg-slate-900 text-slate-200 flex flex-col">
      <div class="px-4 py-4 text-lg font-semibold text-white">LLMOps 控制台</div>
      <nav class="flex-1">
        <RouterLink
          v-for="item in menu"
          :key="item.path"
          :to="item.path"
          class="block px-4 py-2 hover:bg-slate-700"
          active-class="bg-brand"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
      <button class="px-4 py-3 text-left hover:bg-slate-700" @click="logout">退出登录</button>
    </aside>

    <main class="flex-1 overflow-auto bg-slate-50">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

// 角色 → 可见菜单
const menu = computed(() => {
  const base = [
    { path: '/chat', label: '对话' },
    { path: '/agents', label: 'Agent 管理' },
    { path: '/analytics', label: '监控大盘' },
  ]
  if (auth.role === 'admin') base.push({ path: '/admin', label: '管理后台' })
  return base
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>
