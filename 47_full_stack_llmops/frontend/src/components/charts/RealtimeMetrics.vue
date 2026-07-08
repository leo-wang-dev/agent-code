<template>
  <!-- 面板1：实时业务指标（文章 必备面板 1）-->
  <div class="bg-white shadow rounded p-4">
    <div class="font-semibold mb-3">实时业务指标 · 今天</div>
    <div class="grid grid-cols-2 gap-3 mb-4">
      <Stat label="对话数" :value="data?.conversations ?? 0" trend="↑ 18%" />
      <Stat label="独立用户" :value="data?.users ?? 0" trend="↑ 12%" />
      <Stat label="平均满意度" :value="(data?.satisfaction ?? 0) + '/5'" trend="→ 持平" />
      <Stat label="人工升级率" :value="pct(data?.escalation)" trend="↓ 2%" />
    </div>
    <div ref="chartRef" class="w-full h-40"></div>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ data?: { conversations: number; users: number; satisfaction: number; escalation: number } }>()
const chartRef = ref<HTMLDivElement>()

function pct(v?: number) {
  return v == null ? '-' : `${Math.round(v * 100)}%`
}

// 小型 stat 卡片（内联函数组件）
const Stat = (p: { label: string; value: string | number; trend: string }) =>
  h('div', { class: 'bg-slate-50 rounded p-2' }, [
    h('div', { class: 'text-xs text-slate-500' }, p.label),
    h('div', { class: 'text-lg font-semibold' }, String(p.value)),
    h('div', { class: 'text-xs text-slate-400' }, p.trend),
  ])

function render() {
  if (!chartRef.value) return
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: Array.from({ length: 24 }, (_, i) => `${i}:00`) },
    yAxis: { type: 'value' },
    grid: { left: 40, right: 10, top: 10, bottom: 24 },
    series: [{ type: 'line', smooth: true, areaStyle: {}, data: sampleCurve() }],
  })
}

function sampleCurve() {
  return Array.from({ length: 24 }, (_, i) => Math.round(400 + 600 * Math.sin((i / 24) * Math.PI)))
}

onMounted(render)
watch(() => props.data, render)
</script>
