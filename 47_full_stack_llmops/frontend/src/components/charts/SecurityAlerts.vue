<template>
  <!-- 面板5：安全告警（文章 必备面板 5）-->
  <div class="bg-white shadow rounded p-4">
    <div class="font-semibold mb-3">安全监控</div>
    <div class="grid grid-cols-2 gap-3">
      <Metric label="Prompt Injection 拦截" :value="data?.injection ?? 0" />
      <Metric label="Guardrails 触发" :value="data?.guardrail ?? 0" />
      <Metric label="HITL 审批通过率" :value="pct(data?.hitlPass)" />
      <Metric label="异常用户标记" :value="data?.flagged ?? 0" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'

const props = defineProps<{
  data?: { injection: number; guardrail: number; hitlPass: number; flagged: number }
}>()

function pct(v?: number) {
  return v == null ? '-' : `${Math.round(v * 100)}%`
}

const Metric = (p: { label: string; value: string | number }) =>
  h('div', { class: 'bg-slate-50 rounded p-3' }, [
    h('div', { class: 'text-xs text-slate-500' }, p.label),
    h('div', { class: 'text-2xl font-semibold' }, String(p.value)),
  ])
// 使用 props 以避免未使用告警
void props
</script>
