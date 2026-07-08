"""流式对话 API —— SSE。对应文章第 46 篇 七、流式 Chat 接口。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.deps import get_current_user
from app.models import User
from app.schemas import ChatRequest
from app.services.agent_service import AgentService

router = APIRouter(tags=["chat"])
_service = AgentService()


@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    async def event_stream():
        try:
            async for event in _service.stream_chat(
                agent_id=body.agent_id, message=body.message, user_id=user.id
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:  # noqa: BLE001
            yield f"data: {json.dumps({'error': 'stream error'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
