"""Agent 管理 API —— 列表/创建，自动按 tenant 隔离。对应文章第 46 篇 agents.py。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Agent, User
from app.schemas import AgentCreate, AgentOut

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[AgentOut])
async def list_agents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentOut]:
    result = await db.execute(select(Agent).where(Agent.tenant_id == user.tenant_id))
    return [
        AgentOut(id=a.id, tenant_id=a.tenant_id, name=a.name, model=a.model, is_active=a.is_active)
        for a in result.scalars().all()
    ]


@router.post("/", response_model=AgentOut)
async def create_agent(
    body: AgentCreate,
    user: User = Depends(require_admin),   # 需要 admin
    db: AsyncSession = Depends(get_db),
) -> AgentOut:
    agent = Agent(tenant_id=user.tenant_id, **body.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentOut(id=agent.id, tenant_id=agent.tenant_id, name=agent.name,
                    model=agent.model, is_active=agent.is_active)
