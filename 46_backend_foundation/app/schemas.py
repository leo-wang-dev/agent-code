"""Pydantic schema —— API 入参/出参校验。对应文章第 46 篇 schemas/ 层。"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = "gpt-4o"
    temperature: float = 0.2


class AgentOut(BaseModel):
    id: int
    tenant_id: int
    name: str
    model: str | None = None
    is_active: bool = True


class ChatRequest(BaseModel):
    agent_id: int
    session_id: str | None = None
    message: str
