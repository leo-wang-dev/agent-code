<template>
  <!-- 面板2：成本仪表盘（文章 必备面板 2 + ECharts 实现示例）-->
  <div class="bg-white shadow rounded p-4">
    <div class="font-semibold mb-3">成本仪表盘 · 本月</div>
    <div ref="chartRef" class="w-full h-80"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ data: { name: string; value: number }[] }>()
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
        radius: ['40%', '70%'],
        label: { show: true, formatter: '{b}\n{d}%' },
        data: props.data,
      },
    ],
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })
</script>
