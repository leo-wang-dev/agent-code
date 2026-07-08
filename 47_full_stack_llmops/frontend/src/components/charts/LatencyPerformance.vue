<template>
  <!-- 面板3：延迟与性能（文章 必备面板 3）-->
  <div class="bg-white shadow rounded p-4">
    <div class="font-semibold mb-3">延迟与性能</div>
    <div class="grid grid-cols-2 gap-2 mb-3 text-sm">
      <div>TTFT P50/P95/P99: {{ (data?.ttft ?? []).join(' / ') }} ms</div>
      <div>端到端 P50/P95/P99: {{ (data?.e2e ?? []).join(' / ') }} ms</div>
    </div>
    <div ref="chartRef" class="w-full h-64"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  data?: { ttft: number[]; e2e: number[]; composition: { name: string; value: number }[] }
}>()
const chartRef = ref<HTMLDivElement>()

function render() {
  if (!chartRef.value) return
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: '65%',
        label: { formatter: '{b} {d}%' },
        data: props.data?.composition ?? [],
      },
    ],
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })
</script>
