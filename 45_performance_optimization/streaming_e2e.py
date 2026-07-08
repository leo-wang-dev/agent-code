"""流式输出端到端实现 —— 本地 mock 流式生成器 + SSE 编码 + 工具调用/错误处理 + 流式 Guardrails。

对应文章第 45 篇 三、流式输出。

- 服务端：`stream_response` 是本地 mock 流式生成器（真实可跑，不联网），
  `sse_encode` 把每个 event 编成 SSE 帧；
- 覆盖文章四个坑：Nginx buffering（配置见 nginx_streaming.conf）、客户端解析、
  工具调用中间态、流式错误处理；
- 流式 Guardrails：句子块级过滤。

真实可跑：`python3 streaming_e2e.py`
Nginx 配置见同目录 `nginx_streaming.conf`。
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator


async def stream_response(query: str, fail_at: int | None = None) -> AsyncIterator[dict]:
    """本地 mock 流式生成器：逐 token 产出，可选在中途注入工具调用/错误。

    生产替换：
        response = await client.chat.completions.create(..., stream=True)
        async for chunk in response: yield ...
    """
    answer = f"针对「{query}」的回答：先查政策，再给结论。"
    tokens = list(answer)
    for i, tok in enumerate(tokens):
        await asyncio.sleep(0.005)
        if fail_at is not None and i == fail_at:
            raise RuntimeError("upstream provider error")
        # 中途演示一次工具调用中间态（坑3）
        if i == 5:
            yield {"type": "tool_call", "name": "query_policy", "args": {"q": query}}
        yield {"type": "token", "content": tok}
    yield {"type": "done"}


def sse_encode(event: dict) -> str:
    """把一个 event 编成 SSE 帧（坑1：需配合 Nginx proxy_buffering off）。"""
    if event.get("type") == "done":
        return "data: [DONE]\n\n"
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def safe_stream(query: str, fail_at: int | None = None) -> AsyncIterator[str]:
    """坑4：流式中途出错不能直接抛给用户——已经看到一半内容了，追加降级提示。"""
    try:
        async for event in stream_response(query, fail_at=fail_at):
            yield sse_encode(event)
    except Exception as e:  # noqa: BLE001
        yield sse_encode({"type": "token", "content": f"\n\n[系统错误，请稍后重试: {e}]"})
        yield sse_encode({"type": "done"})


def _sentence_ended(buf: str) -> bool:
    return buf.endswith(("。", "！", "？", ".", "!", "?"))


def _has_violation(text: str) -> bool:
    return any(bad in text for bad in ["身份证", "银行卡", "密码"])


async def streamed_guardrails(query: str) -> AsyncIterator[str]:
    """流式 Guardrails：攒到一个完整句子块才做一次快速过滤（做法1）。"""
    buffer = ""
    async for event in stream_response(query):
        if event["type"] != "token":
            continue
        buffer += event["content"]
        if _sentence_ended(buffer):
            if _has_violation(buffer):
                yield "[内容被过滤]"
                return
            yield buffer
            buffer = ""
    if buffer:
        yield buffer


async def client_consume(query: str) -> str:
    """模拟浏览器端流式读取（坑2：逐块读，累积 token）。"""
    collected = []
    async for frame in safe_stream(query):
        for line in frame.splitlines():
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                return "".join(collected)
            event = json.loads(data)
            if event.get("type") == "token":
                collected.append(event["content"])
    return "".join(collected)


async def _demo() -> None:
    print("=== 正常流式（客户端累积）===")
    text = await client_consume("我要退货")
    print("  收到:", text)

    print("\n=== 流式中途出错（坑4：优雅降级）===")
    text = await client_consume("查询订单")  # fail_at 由 safe_stream 默认 None
    # 触发一次真实失败
    async for frame in safe_stream("查询订单", fail_at=6):
        pass
    print("  出错后仍能收到降级提示（见 safe_stream 实现）")

    print("\n=== 流式 Guardrails（句子块级过滤）===")
    async for chunk in streamed_guardrails("介绍产品"):
        print("  块:", chunk)


if __name__ == "__main__":
    asyncio.run(_demo())
