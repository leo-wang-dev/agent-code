// API 客户端基座 —— 统一注入 JWT、处理 401。对应文章第 47 篇 api/ 层。
import { useAuthStore } from '@/stores/auth'

const BASE = '/api/v1'

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const auth = useAuthStore()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (auth.token) headers['Authorization'] = `Bearer ${auth.token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    auth.logout()
    throw new Error('unauthorized')
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as T
}

export function getToken(): string | null {
  return useAuthStore().token
}
