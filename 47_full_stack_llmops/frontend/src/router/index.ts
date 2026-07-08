import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 对应文章第 47 篇 一、项目骨架 —— Vue Router + 登录守卫。
const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('@/views/auth/Login.vue'), meta: { public: true } },
  { path: '/', redirect: '/chat' },
  { path: '/chat', component: () => import('@/views/chat/Chat.vue') },
  { path: '/agents', component: () => import('@/views/agents/Agents.vue') },
  { path: '/analytics', component: () => import('@/views/analytics/Analytics.vue') },
  { path: '/admin', component: () => import('@/views/admin/Admin.vue'), meta: { role: 'admin' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) return '/login'
  if (to.meta.role && auth.role !== to.meta.role) return '/chat'
  return true
})

export default router
