"""产物：流式输出是什么（对应文章 §五 "流式输出是什么"）。

stream=true 之后，响应不再是一个完整 JSON，而是一串 Server-Sent Events：每行
`data: {...}`，客户端把 delta.content 拼起来才是完整回答，最后以 `data: [DONE]` 收尾。

本文件：
  1. 用一段"离线 SSE 原始字节"模拟服务器推流，逐个事件解析、拼接（不发网络）；
  2. 用仓库内 StreamAssembler 把 content 与 tool_calls 参数分别攒齐；
  3. 打印 TTFT / TPS 两个关键指标，并说明为什么 LLM 场景选 SSE 而不是 WebSocket。

    python3 streaming_sse.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import StreamAssembler


# 模拟服务器推来的原始 SSE 文本（含最后的 [DONE] 哨兵）。
RAW_SSE = """\
data: {"choices":[{"delta":{"content":"BPE"}}]}

data: {"choices":[{"delta":{"content":" 是"}}]}

data: {"choices":[{"delta":{"content":"一种"}}]}

data: {"choices":[{"delta":{"content":"分词"}}]}

data: {"choices":[{"delta":{"content":"算法"}}]}

data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":28,"completion_tokens":5,"total_tokens":33}}

data: [DONE]
"""

# 每个 chunk 到达的相对时间戳（毫秒），用来算 TTFT / TPS。首 token 在 300ms 到达。
ARRIVAL_MS = [300, 340, 380, 420, 470, 480]


def parse_sse(raw: str) -> list[dict]:
    """把 SSE 文本切成一个个 JSON 事件，跳过 [DONE] 哨兵与空行。"""
    events: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        events.append(json.loads(payload))
    return events


def main() -> None:
    print("① 原始 SSE（服务器一行一行推过来）")
    for line in RAW_SSE.splitlines():
        if line.strip():
            print("    " + line)

    events = parse_sse(RAW_SSE)
    assembler = StreamAssembler()
    for event in events:
        assembler.push_event(event)

    print("\n② 客户端把 delta.content 拼起来")
    print(f"    完整回答 → {assembler.text()}")
    print(f"    usage    → {assembler.usage}  (stream_options.include_usage 才拿得到)")

    print("\n③ 两个关键指标")
    ttft = ARRIVAL_MS[0]
    total_ms = ARRIVAL_MS[-1]
    n_tokens = assembler.usage["completion_tokens"] if assembler.usage else len(ARRIVAL_MS)
    tps = n_tokens / (total_ms / 1000.0)
    print(f"    TTFT = {ttft} ms   ← 用户感知的响应速度，体验 90% 由它决定")
    print(f"    TPS  = {tps:.1f} tok/s ← 整个回答吐完的速度")
    print("    TTFT=300ms 的系统，体感好过 TTFT=2s 的，哪怕后者总耗时更短。")

    print("\n④ 为什么是 SSE 不是 WebSocket")
    print("    LLM 推理是单向流：服务器源源不断推，客户端不需要反向通信。")
    print("    SSE 走普通 HTTP，天然穿透代理/防火墙、断线自动重连、无需心跳。")
    print("    工程难点：半路断连、Function Calling 参数要攒齐 JSON、Nginx 要关 proxy_buffering。")


if __name__ == "__main__":
    main()
