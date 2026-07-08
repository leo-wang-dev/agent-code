<template>
  <div v-html="rendered" class="prose prose-sm max-w-none" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'

// 对应文章第 47 篇 三、Markdown + 代码高亮。DOMPurify 防 XSS 是必须的。
const props = defineProps<{ content: string }>()

const rendered = computed(() => {
  const renderer = new marked.Renderer()
  renderer.code = (code: string, lang?: string) => {
    const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
    const highlighted = hljs.highlight(code, { language }).value
    return `<pre><code class="hljs ${language}">${highlighted}</code></pre>`
  }
  const html = marked.parse(props.content, { renderer }) as string
  return DOMPurify.sanitize(html)
})
</script>
