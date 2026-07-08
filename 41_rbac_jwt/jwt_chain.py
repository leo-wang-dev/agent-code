"""JWT 全链路传递完整 demo。

对应文章第二节。用户登录签发 JWT → Agent 应用存入 ToolContext → Tool 内部用
JWT 调下游 → 下游用 JWT 里的用户身份做权限过滤（而非 Agent 服务账号权限）。

两条铁律：
  1. JWT 严禁进入 LLM 上下文（LLM 可能写进输出/日志 = 泄露）——只存 ToolContext；
  2. 下游用 JWT 的用户身份过滤数据，服务账号只有"代表用户访问"的权限。

JWT 用 stdlib hmac 实现 HS256 教学版（无第三方依赖）。
生产请用 `pyjwt`（pip install pyjwt）并改用非对称 RS256/ES256 + 密钥轮换。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field

SECRET_KEY = "teaching-secret-do-not-use-in-prod"  # 生产：从 KMS/密钥管理取，用 RS256


# ---------------------------------------------------------------------------
# 教学版 JWT（HS256）—— 生产用 pyjwt
# ---------------------------------------------------------------------------
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def jwt_encode(payload: dict, secret: str = SECRET_KEY) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"


def jwt_decode(token: str, secret: str = SECRET_KEY) -> dict:
    try:
        h, p, s = token.split(".")
    except ValueError as e:
        raise ValueError("JWT 格式错误") from e
    expected = _b64url(
        hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(expected, s):  # 防时序攻击
        raise ValueError("JWT 签名校验失败")
    payload = json.loads(_b64url_decode(p))
    if payload.get("exp", 1e18) < time.time():
        raise ValueError("JWT 已过期")
    return payload


# ---------------------------------------------------------------------------
# ToolContext：JWT 只存这里，不进 LLM
# ---------------------------------------------------------------------------
@dataclass
class UserClaims:
    user_id: str
    roles: list[str]
    permissions: list[str]
    tenant_id: str


@dataclass
class ToolContext:
    user: UserClaims
    user_jwt: str  # 原始 JWT，仅工具内部调下游用
    acting_agent: str = "unknown"


# ---------------------------------------------------------------------------
# 1. 登录签发
# ---------------------------------------------------------------------------
def login(user_id: str, roles: list[str], permissions: list[str], tenant_id: str) -> str:
    now = int(time.time())
    return jwt_encode(
        {
            "user_id": user_id,
            "roles": roles,
            "permissions": permissions,
            "tenant_id": tenant_id,
            "iat": now,
            "exp": now + 3600,
        }
    )


# ---------------------------------------------------------------------------
# 2. Agent 接收请求 → ToolContext
# ---------------------------------------------------------------------------
def build_context(jwt_token: str, agent_name: str) -> ToolContext:
    claims = jwt_decode(jwt_token)
    user = UserClaims(
        user_id=claims["user_id"],
        roles=claims["roles"],
        permissions=claims["permissions"],
        tenant_id=claims["tenant_id"],
    )
    return ToolContext(user=user, user_jwt=jwt_token, acting_agent=agent_name)


def build_llm_prompt(ctx: ToolContext, query: str) -> str:
    # 正确做法：只放 user_id，JWT 绝不进 prompt
    return f"User: {ctx.user.user_id}, query: {query}"


# ---------------------------------------------------------------------------
# 3. Tool 内部用 JWT 调下游（此处 mock 下游）
# ---------------------------------------------------------------------------
def query_contracts(filters: dict, tool_context: ToolContext) -> list:
    # 关键：把用户 JWT 加到下游请求头（这里 mock，不发真实网络）
    headers = {
        "Authorization": f"Bearer {tool_context.user_jwt}",
        "X-Acting-Agent": tool_context.acting_agent,
    }
    # 下游：用 JWT 里的用户身份过滤，而非返回全表
    downstream_claims = jwt_decode(tool_context.user_jwt)
    return _mock_downstream_db(downstream_claims, filters, headers)


def _mock_downstream_db(claims: dict, filters: dict, headers: dict) -> list:
    # 模拟 SQL: WHERE owner_id IN (用户可见客户) AND tenant_id = 用户租户
    return [
        {"contract_id": "C1", "owner_id": claims["user_id"], "tenant_id": claims["tenant_id"]},
        {"contract_id": "C2", "owner_id": claims["user_id"], "tenant_id": claims["tenant_id"]},
    ]


def main() -> None:
    print("=" * 60)
    print("JWT 全链路传递 demo")
    print("=" * 60)
    token = login("u_1001", ["sales"], ["contract.read"], tenant_id="acme")
    print(f"\n1. 签发 JWT: {token[:48]}...")

    ctx = build_context(token, "sales_assistant")
    print(f"2. 解析入 ToolContext: user={ctx.user.user_id} tenant={ctx.user.tenant_id}")

    prompt = build_llm_prompt(ctx, "查一下我名下的合同")
    print(f"3. 给 LLM 的 prompt（不含 JWT）: {prompt}")

    rows = query_contracts({"status": "active"}, ctx)
    print(f"4. Tool 用 JWT 调下游 → 用户身份过滤，返回 {len(rows)} 条: {rows}")

    print("\n-- 篡改/过期校验 --")
    for bad, label in [(token[:-2] + "xy", "篡改签名"), (login("u", [], [], "t").replace(".", ".x", 1), "破坏结构")]:
        try:
            jwt_decode(bad)
            print(f"  [{label}] 未拦截（异常）")
        except ValueError as e:
            print(f"  [{label}] 已拒绝: {e}")


if __name__ == "__main__":
    main()
