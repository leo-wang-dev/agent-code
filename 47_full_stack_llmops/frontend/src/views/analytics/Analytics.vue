<template>
  <div class="p-6 space-y-6">
    <h1 class="text-xl font-semibold">监控大盘</h1>
    <!-- 5 大面板（文章二、监控大盘的关键面板）-->
    <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <RealtimeMetrics :data="data?.realtime" />
      <CostBreakdown :data="data?.cost ?? []" />
      <LatencyPerformance :data="data?.latency" />
      <QualityMonitor :data="data?.quality ?? []" />
      <SecurityAlerts :data="data?.security" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchDashboard, type DashboardData } from '@/api/analytics'
import RealtimeMetrics from '@/components/charts/RealtimeMetrics.vue'
import CostBreakdown from '@/components/charts/CostBreakdown.vue'
import LatencyPerformance from '@/components/charts/LatencyPerformance.vue'
import QualityMonitor from '@/components/charts/QualityMonitor.vue'
import SecurityAlerts from '@/components/charts/SecurityAlerts.vue'

const data = ref<DashboardData>()

onMounted(async () => {
  try {
    data.value = await fetchDashboard()
  } catch {
    // 后端未接通时用占位数据，保证面板可渲染
    data.value = {
      realtime: { conversations: 12453, users: 3201, satisfaction: 4.6, escalation: 0.08 },
      cost: [
        { name: '客服', value: 42 },
        { name: '研究', value: 28 },
        { name: '代码', value: 18 },
        { name: '其他', value: 12 },
      ],
      latency: {
        ttft: [480, 1200, 2800],
        e2e: [2400, 5100, 9800],
        composition: [
          { name: 'LLM 推理', value: 45 },
          { name: 'RAG 检索', value: 20 },
          { name: '工具调用', value: 18 },
          { name: '网络', value: 12 },
          { name: '其他', value: 5 },
        ],
      },
      quality: [
        { metric: 'Context Precision', score: 85 },
        { metric: 'Faithfulness', score: 91 },
        { metric: 'Answer Relevancy', score: 88 },
      ],
      security: { injection: 42, guardrail: 128, hitlPass: 0.89, flagged: 7 },
    }
  }
})
</script>
