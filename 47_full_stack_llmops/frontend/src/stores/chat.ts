import { defineStore } from 'pinia'
import { streamChat } from '@/api/chat'

// 对应文章第 47 篇 三、聊天界面 —— 会话状态 + 流式追加。
export interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatState {
  sessionId: string
  messages: Message[]
  streaming: boolean
}

export const useChatStore = defineStore('chat', {
  state: (): ChatState => ({
    sessionId: crypto.randomUUID(),
    messages: [],
    streaming: false,
  }),
  actions: {
    async send(agentId: number, text: string) {
      this.messages.push({ role: 'user', content: text })
      const assistant: Message = { role: 'assistant', content: '' }
      this.messages.push(assistant)
      this.streaming = true

      await streamChat(
        agentId,
        this.sessionId,
        text,
        (token) => {
          assistant.content += token
        },
        () => {
          this.streaming = false
        },
        (err) => {
          assistant.content += `\n\n[系统错误：${err.message}]`
          this.streaming = false
        },
      )
    },
    reset() {
      this.sessionId = crypto.randomUUID()
      this.messages = []
    },
  },
})
