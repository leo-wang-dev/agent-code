// 流式对话 API —— SSE 逐块读取。对应文章第 47 篇 三、流式输出的前端实现。
import { getToken } from './client'

export async function streamChat(
  agentId: number,
  sessionId: string,
  message: string,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (error: Error) => void,
): Promise<void> {
  try {
    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ agent_id: agentId, session_id: sessionId, message }),
    })

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value)
      const lines = buffer.split('\n')
      buffer = lines.pop()! // 保留可能不完整的最后一行

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[DONE]') {
          onDone()
          return
        }
        try {
          const event = JSON.parse(data)
          if (event.token) onToken(event.token)
          else if (event.content) onToken(event.content)
          else if (event.error) throw new Error(event.error)
        } catch (e) {
          console.error('parse error', e)
        }
      }
    }
    onDone()
  } catch (e) {
    onError(e as Error)
  }
}
