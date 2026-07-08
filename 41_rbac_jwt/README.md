# 41 · 权限控制与 JWT 与 RBAC —— Agent 多租户隔离

配套文章：《权限控制与 JWT 与 RBAC —— Agent 多租户隔离》（系列第 41 篇）

## 产物对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| JWT 全链路传递完整 demo | `jwt_chain.py` | 登录签发 → ToolContext → Tool 用 JWT 调下游，JWT 不进 LLM |
| 工具级 RBAC 实现 | `tool_rbac.py` | 用户 ∩ Agent 工具池 ∩ Tool 权限，高危走 HITL |
| 多租户隔离中间件 | `multitenant_middleware.py` | tenant_id 只从 JWT 取，参数携带即视为攻击；向量库强制过滤 |
| Agent-to-Agent 权限降级 | `a2a_permission.py` | 身份透传 + 最小权限降级派生 context |
| 完整审计日志系统 | `audit_log.py` | append-only 哈希链防篡改 + 参数脱敏 + 多维查询 |

## 运行

```bash
python3 jwt_chain.py                 # JWT 全链路 + 篡改/过期校验
python3 tool_rbac.py                 # 工具级 RBAC 双向校验
python3 multitenant_middleware.py    # 多租户隔离 + 越权拦截
python3 a2a_permission.py            # A2A 透传与降级
python3 audit_log.py                 # 审计哈希链 + 篡改检出
```

## 生产替代

- JWT：`pip install pyjwt`，用非对称 RS256/ES256 + 密钥轮换；本仓用 stdlib hmac HS256 教学版。
- 审计存储：加密（AES-256，`cryptography` 库）+ WORM 存储 + KMS 管密钥；本仓用哈希链演示防篡改，明文导出仅供演示。
- Tool 参数：生产用 Pydantic 严格 schema 校验防 SQL 注入（文章第七节细节 3）。
- JWT 过期/HITL 续期：用 refresh token + 快照令牌（文章第七节细节 1、2）。
