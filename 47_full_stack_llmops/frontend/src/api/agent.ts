import { request } from './client'

// 对应文章第 47 篇 —— Agent 管理接口。
export interface Agent {
  id: number
  tenant_id: number
  name: string
  model?: string
  is_active: boolean
}

export function listAgents(): Promise<Agent[]> {
  return request<Agent[]>('/agents/')
}

export function createAgent(payload: Partial<Agent>): Promise<Agent> {
  return request<Agent>('/agents/', { method: 'POST', body: JSON.stringify(payload) })
}
