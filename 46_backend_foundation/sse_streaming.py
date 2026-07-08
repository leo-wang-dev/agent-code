"""流式 SSE 完整 demo —— 后端异步生成器 + SSE 编码 + FastAPI 路由（可选）。

对应文章第 46 篇 七、流式 Chat 接口。

- 核心 `agent_event_stream` / `sse_encode` 纯标准库，离线可跑；
- 若装了 FastAPI，`build_router()` 返回一个真实的 `/chat/stream` SSE 路由，
  可挂到 app/main.py（缺 FastAPI 时返回 None 并打印指引，不报错）。

离线可运行：`python3 sse_streaming.py`
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

try:
    from fastapi import APIRouter
    from fastapi.responses import StreamingResponse

    _HAS_FASTAPI = True
except Exception:  # pragma: no cover
    APIRouter = None  # type: ignore
    StreamingResponse = None  # type: ignore
    _HAS_FASTAPI = False


async def agent_event_stream(message: str) -> AsyncIterator[dict]:
    """Agent 编排的流式事件源（本地 mock）。

    生产替换：async for event in agent_service.stream_chat(...): yield event
    """
    answer = f"收到「{message}」，正在处理：先查知识库，再综合回答。"
    for tok in answer:
        await asyncio.sleep(0.003)
        yield {"type": "token", "content": tok}
    yield {"type": "status", "status": "completed"}


def sse_encode(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def build_router():
    """构造 FastAPI SSE 路由；缺 FastAPI 时返回 None。"""
    if not _HAS_FASTAPI:
        return None

    router = APIRouter()

    @router.post("/chat/stream")
    async def chat_stream(body: dict):  # noqa: ANN001
        async def event_stream():
            try:
                async for event in agent_event_stream(body.get("message", "")):
                    yield sse_encode(event)
                yield "data: [DONE]\n\n"
            except Exception:  # noqa: BLE001
                yield sse_encode({"type": "error", "error": "stream error"})

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router


async def _demo() -> None:
    print("=== 后端 SSE 事件流（离线）===")
    frames = []
    async for event in agent_event_stream("我要退货"):
        frames.append(sse_encode(event))
    # 打印前几帧 + 汇总
    for f in frames[:3]:
        print("  " + f.strip())
    print(f"  ... 共 {len(frames)} 帧")
    collected = "".join(
        json.loads(f[6:].strip())["content"]
        for f in frames
        if json.loads(f[6:].strip()).get("type") == "token"
    )
    print("  客户端拼回:", collected)

    print("\n=== FastAPI 路由 ===")
    router = build_router()
    if router is None:
        print("  未安装 FastAPI，跳过路由构造。生产安装：pip install fastapi uvicorn")
    else:
        print(f"  已构造 SSE 路由，路由数={len(router.routes)}，可挂到 app/main.py")


if __name__ == "__main__":
    asyncio.run(_demo())
