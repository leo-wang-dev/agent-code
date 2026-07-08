<template>
  <!-- 面板4：质量监控（文章 必备面板 4）-->
  <div class="bg-white shadow rounded p-4">
    <div class="font-semibold mb-3">质量监控 · 评测集分数</div>
    <div ref="chartRef" class="w-full h-72"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ data: { metric: string; score: number }[] }>()
const chartRef = ref<HTMLDivElement>()

function render() {
  if (!chartRef.value) return
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: {},
    radar: {
      indicator: props.data.map((d) => ({ name: d.metric, max: 100 })),
    },
    series: [
      {
        type: 'radar',
        data: [{ value: props.data.map((d) => d.score), name: '本周评测' }],
        areaStyle: {},
      },
    ],
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })
</script>
