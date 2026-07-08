import { request } from './client'

// 对应文章第 47 篇 二、监控大盘 —— 拉取各面板数据。
export interface DashboardData {
  realtime: { conversations: number; users: number; satisfaction: number; escalation: number }
  cost: { name: string; value: number }[]
  latency: { ttft: number[]; e2e: number[]; composition: { name: string; value: number }[] }
  quality: { metric: string; score: number }[]
  security: { injection: number; guardrail: number; hitlPass: number; flagged: number }
}

export function fetchDashboard(): Promise<DashboardData> {
  return request<DashboardData>('/analytics/dashboard')
}
