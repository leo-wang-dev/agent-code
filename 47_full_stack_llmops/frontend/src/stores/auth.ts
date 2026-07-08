import { defineStore } from 'pinia'

// 对应文章第 47 篇 —— Pinia 鉴权状态。token 解析出 role/tenant（教学：不校验签名，仅读 payload）。
interface AuthState {
  token: string | null
  role: string
  tenantId: number | null
}

function parseRole(token: string): { role: string; tenantId: number | null } {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return { role: payload.role ?? 'user', tenantId: payload.tenant_id ?? null }
  } catch {
    return { role: 'user', tenantId: null }
  }
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('token'),
    role: 'user',
    tenantId: null,
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    setToken(token: string) {
      this.token = token
      localStorage.setItem('token', token)
      const { role, tenantId } = parseRole(token)
      this.role = role
      this.tenantId = tenantId
    },
    logout() {
      this.token = null
      this.role = 'user'
      this.tenantId = null
      localStorage.removeItem('token')
    },
  },
})
