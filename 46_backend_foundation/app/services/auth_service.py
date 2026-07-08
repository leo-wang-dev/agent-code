"""认证业务服务 —— 注册/建管理员。对应文章第 46 篇 services/auth_service.py。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant, User
from app.security import hash_password


class AuthService:
    async def register(
        self, db: AsyncSession, email: str, password: str, tenant_id: int, role: str = "user"
    ) -> User:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            tenant_id=tenant_id,
            role=role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def ensure_demo_tenant(self, db: AsyncSession) -> Tenant:
        result = await db.execute(select(Tenant).where(Tenant.name == "Demo Tenant"))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name="Demo Tenant", plan="pro")
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
        return tenant
