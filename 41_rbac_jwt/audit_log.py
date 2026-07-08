"""完整审计日志系统。

对应文章第六节。Agent 审计必须能回答："哪个用户、通过哪个 Agent、调用了哪个
工具、对哪条数据、做了什么、什么结果"。

存储要求：
  不可篡改（append-only + 哈希链，删除走特殊审批）、加密存储（AES-256）、
  保留期（业务 90 天 / 合规 6 月-7 年）、可按用户/时间/Agent/工具查询、可导出。

本文件用 stdlib 实现：
  - append-only 哈希链（每条记录含前一条 hash，任意篡改可被 verify_chain 检出）
  - 参数脱敏
  - 多维度查询
加密存储用注释标注生产替代（cryptography/KMS），演示不引入依赖。
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field


def sanitize(args: dict) -> dict:
    """参数脱敏：遮掉手机号/邮箱/疑似密钥。"""
    out = {}
    for k, v in args.items():
        if isinstance(v, str):
            v = re.sub(r"\b1[3-9]\d{9}\b", "[PHONE]", v)
            v = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL]", v)
        if k.lower() in {"password", "token", "secret", "jwt"}:
            v = "[REDACTED]"
        out[k] = v
    return out


@dataclass
class AuditRecord:
    user_id: str
    user_roles: list[str]
    tenant_id: str
    session_id: str
    trace_id: str
    agent_name: str
    agent_version: str
    tool_name: str
    tool_args: dict
    tool_result_summary: str
    permission_check: str
    outcome: str
    duration_ms: int
    hitl_approved_by: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["tool_args"] = sanitize(self.tool_args)
        return d


class AuditLog:
    """append-only 哈希链审计日志。"""

    GENESIS = "0" * 64

    def __init__(self) -> None:
        self._chain: list[dict] = []

    def _prev_hash(self) -> str:
        return self._chain[-1]["hash"] if self._chain else self.GENESIS

    def append(self, record: AuditRecord) -> str:
        payload = record.to_dict()
        prev = self._prev_hash()
        block = {"prev": prev, "record": payload}
        h = hashlib.sha256(
            (prev + json.dumps(payload, sort_keys=True, ensure_ascii=False)).encode()
        ).hexdigest()
        block["hash"] = h
        self._chain.append(block)
        return h

    def verify_chain(self) -> tuple[bool, int]:
        """校验哈希链完整性，返回 (是否完整, 首个被篡改的位置或 -1)。"""
        prev = self.GENESIS
        for i, block in enumerate(self._chain):
            expected = hashlib.sha256(
                (prev + json.dumps(block["record"], sort_keys=True, ensure_ascii=False)).encode()
            ).hexdigest()
            if block["prev"] != prev or block["hash"] != expected:
                return False, i
            prev = block["hash"]
        return True, -1

    def query(self, **filters) -> list[dict]:  # noqa: ANN003
        """按 user_id / agent_name / tool_name / tenant_id 等维度筛选。"""
        results = []
        for block in self._chain:
            rec = block["record"]
            if all(rec.get(k) == v for k, v in filters.items()):
                results.append(rec)
        return results

    def export(self) -> str:
        # 生产：加密后导出（AES-256）。此处返回明文 JSON 供演示。
        return json.dumps([b["record"] for b in self._chain], ensure_ascii=False, indent=2)


def main() -> None:
    print("=" * 60)
    print("审计日志系统演示（append-only + 哈希链）")
    print("=" * 60)
    log = AuditLog()
    log.append(AuditRecord(
        user_id="u_1001", user_roles=["sales"], tenant_id="acme",
        session_id="s1", trace_id="t1", agent_name="sales_assistant",
        agent_version="v1.2.3", tool_name="query_contracts",
        tool_args={"phone": "13800138000", "status": "active"},
        tool_result_summary="返回 15 条记录", permission_check="passed",
        outcome="success", duration_ms=1234,
    ))
    log.append(AuditRecord(
        user_id="u_admin", user_roles=["admin"], tenant_id="acme",
        session_id="s2", trace_id="t2", agent_name="admin_assistant",
        agent_version="v1.2.3", tool_name="delete_customer",
        tool_args={"customer_id": 42, "token": "abc"},
        tool_result_summary="删除 1 条", permission_check="passed",
        outcome="success", duration_ms=560, hitl_approved_by="mgr_zhang",
    ))

    ok, pos = log.verify_chain()
    print(f"\n哈希链完整性：{'完整 ✅' if ok else f'被篡改@{pos} ❌'}")

    print("\n按 user_id=u_admin 查询：")
    for rec in log.query(user_id="u_admin"):
        print(f"  {rec['agent_name']} → {rec['tool_name']}  args={rec['tool_args']}  批准人={rec['hitl_approved_by']}")

    print("\n-- 模拟篡改历史记录 --")
    log._chain[0]["record"]["outcome"] = "tampered"
    ok, pos = log.verify_chain()
    print(f"篡改后校验：{'完整' if ok else f'检出篡改@{pos} ✅（哈希链生效）'}")


if __name__ == "__main__":
    main()
