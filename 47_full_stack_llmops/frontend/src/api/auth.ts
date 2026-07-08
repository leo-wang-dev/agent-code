import { request } from './client'

// 对应文章第 47 篇 —— 登录接口。
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}
