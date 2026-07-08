<template>
  <div class="p-6">
    <h1 class="text-xl font-semibold mb-4">管理后台</h1>
    <p class="text-slate-500 mb-4">仅 admin 可见：用户 / 计费 / 全局配置。</p>
    <div class="grid grid-cols-3 gap-4">
      <div v-for="c in cards" :key="c.title" class="bg-white shadow rounded p-4">
        <div class="text-slate-500 text-sm">{{ c.title }}</div>
        <div class="text-2xl font-semibold">{{ c.value }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 占位管理后台——实际接 /admin 接口。对应文章第 47 篇角色差异化。
const cards = [
  { title: '租户数', value: 12 },
  { title: '活跃用户', value: 3201 },
  { title: '本月成本', value: '$12,453' },
]
</script>
