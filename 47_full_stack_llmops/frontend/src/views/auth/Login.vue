<template>
  <div class="h-full flex items-center justify-center">
    <div class="w-80 bg-white rounded-lg shadow p-6">
      <h1 class="text-xl font-semibold mb-4">登录 LLMOps 控制台</h1>
      <input v-model="email" placeholder="邮箱" class="w-full border rounded px-3 py-2 mb-3" />
      <input
        v-model="password"
        type="password"
        placeholder="密码"
        class="w-full border rounded px-3 py-2 mb-3"
        @keyup.enter="submit"
      />
      <p v-if="error" class="text-red-500 text-sm mb-2">{{ error }}</p>
      <button class="w-full bg-brand text-white rounded py-2" @click="submit">登录</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const email = ref('demo@example.com')
const password = ref('')
const error = ref('')
const router = useRouter()
const auth = useAuthStore()

async function submit() {
  error.value = ''
  try {
    const res = await login(email.value, password.value)
    auth.setToken(res.access_token)
    router.push('/chat')
  } catch (e) {
    error.value = (e as Error).message
  }
}
</script>
