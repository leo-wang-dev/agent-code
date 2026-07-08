# 02 · 一次 LLM 调用，到底发生了什么？

对应文章《一次 LLM 调用，到底发生了什么？》（系列第 02 篇）。

把一次 LLM 调用剥掉所有框架包装，还原成一个普通的无状态 REST API。每个文件对应文章里的一层，全部离线可跑（无 `OPENAI_API_KEY` 时不发任何网络请求，用确定性 mock）。

## 产物 → 文件 → 运行命令

| 文章对应 | 产物 | 文件 | 运行命令 |
|---|---|---|---|
| §一 它就是一个普通的 REST API | 裸 HTTP 请求形态 + id/usage/finish_reason 三字段 | `raw_http_request.py` | `python3 raw_http_request.py` |
| §二 messages 的三种角色 | 无状态 messages / 多轮对话逐字重发 | `stateless_messages.py` | `python3 stateless_messages.py` |
| §三 Token 的本质 | 分词估算 + 128k 上下文预算拆解 | `token_budget.py` | `python3 token_budget.py` |
| §四 temperature 调的是什么 | 概率分布采样与温度对比 | `temperature_sampling.py` | `python3 temperature_sampling.py` |
| §五 流式输出是什么 | SSE 解析拼接 + TTFT/TPS 指标 | `streaming_sse.py` | `python3 streaming_sse.py` |
| 汇总 | HTTP + 流式一把跑 | `run_demo.py` | `python3 run_demo.py` |

## 一次跑全部

```bash
for f in raw_http_request stateless_messages token_budget temperature_sampling streaming_sse; do
  echo "===== $f ====="; python3 "$f.py"; echo
done
```

## 复用的核心实现

这些示例复用仓库 `src/agent_code/llm_call.py` 里的：`ChatMessage` / `LLMRequest` / `StreamAssembler` / `estimate_tokens` / `sample_next_token` / `build_raw_http_request`。示例只负责把"本质"演示出来，工程实现沉淀在 `src/` 里。
