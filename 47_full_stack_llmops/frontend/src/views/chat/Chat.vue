<template>
  <div class="h-full flex flex-col">
    <div class="flex-1 overflow-auto p-6 space-y-4">
      <div v-for="(m, i) in chat.messages" :key="i" class="flex" :class="m.role === 'user' ? 'justify-end' : ''">
        <div
          class="max-w-2xl rounded-lg px-4 py-2"
          :class="m.role === 'user' ? 'bg-brand text-white' : 'bg-white shadow'"
        >
          <MessageContent v-if="m.role === 'assistant'" :content="m.content" />
          <span v-else>{{ m.content }}</span>
        </div>
      </div>
    </div>

    <div class="border-t p-4 flex gap-2">
      <input
        v-model="draft"
        placeholder="输入消息…"
        class="flex-1 border rounded px-3 py-2"
        :disabled="chat.streaming"
        @keyup.enter="send"
      />
      <button class="bg-brand text-white rounded px-5" :disabled="chat.streaming" @click="send">
        发送
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import MessageContent from '@/components/chat/MessageContent.vue'

const chat = useChatStore()
const draft = ref('')
const currentAgentId = 1 // 实际从 Agent 选择器取

async function send() {
  const text = draft.value.trim()
  if (!text) return
  draft.value = ''
  await chat.send(currentAgentId, text)
}
</script>
