"""配置 —— 从环境变量读取，带开发默认值。生产用 pydantic-settings + .env。"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://agent:agent@localhost:5432/agent_platform"
    )
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379")
    llm_gateway_url: str = os.environ.get("LLM_GATEWAY_URL", "http://localhost:4000/v1")
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-only-change-me")
    access_token_ttl: int = 3600
    rate_limit_per_minute: int = 60


settings = Settings()
