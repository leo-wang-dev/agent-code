"""Agent 业务服务 —— 编排 + 流式。对应文章第 46 篇 services/agent_service.py。

业务逻辑层：不碰 HTTP 细节，也不碰 SQL 细节（交给 Repository/Model）。
这里的流式是本地 mock；生产接 LLM Gateway + 真实编排器。
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator


class AgentService:
    async def stream_chat(
        self, agent_id: int, message: str, user_id: int
    ) -> AsyncIterator[dict]:
        # 生产：加载 agent、取会话历史、调编排器、落库 token_usage / messages
        answer = f"[agent {agent_id}] 收到「{message}」，正在为您处理。"
        for tok in answer:
            await asyncio.sleep(0.002)
            yield {"type": "token", "content": tok}
        yield {"type": "status", "status": "completed"}
