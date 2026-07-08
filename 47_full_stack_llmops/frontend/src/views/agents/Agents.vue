<template>
  <div class="p-6">
    <h1 class="text-xl font-semibold mb-4">Agent 管理</h1>
    <table class="w-full bg-white shadow rounded overflow-hidden">
      <thead class="bg-slate-100 text-left">
        <tr>
          <th class="px-4 py-2">ID</th>
          <th class="px-4 py-2">名称</th>
          <th class="px-4 py-2">模型</th>
          <th class="px-4 py-2">状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in agents" :key="a.id" class="border-t">
          <td class="px-4 py-2">{{ a.id }}</td>
          <td class="px-4 py-2">{{ a.name }}</td>
          <td class="px-4 py-2">{{ a.model }}</td>
          <td class="px-4 py-2">
            <span :class="a.is_active ? 'text-green-600' : 'text-slate-400'">
              {{ a.is_active ? '启用' : '停用' }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAgents, type Agent } from '@/api/agent'

const agents = ref<Agent[]>([])

onMounted(async () => {
  try {
    agents.value = await listAgents()
  } catch {
    agents.value = []
  }
})
</script>
