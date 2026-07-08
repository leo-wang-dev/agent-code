"""虚拟 Key 治理面板 —— 对应第 35 篇「六、必做 1：建立虚拟 Key 治理规范」。

实现虚拟 Key 的自助申请 / 审批 / 预算上限 / 过期 / 闲置回收 review。
纯标准库、sqlite 落库：
    python3 35_gateway_implementation/virtual_key_panel.py
"""

from __future__ import annotations

import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

DB_PATH = str(Path(__file__).resolve().parent / ".vkey_panel.db")


@dataclass
class KeyRequest:
    owner: str
    project: str
    budget_usd: float
    allowed_models: list[str]
    ttl_days: int


class VirtualKeyPanel:
    """虚拟 Key 治理：每个 Key 有明确所有者 + 预算上限 + 过期时间。"""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS vkeys ("
            "key TEXT PRIMARY KEY, owner TEXT, project TEXT, budget REAL, models TEXT, "
            "status TEXT, created REAL, expires REAL, spent REAL DEFAULT 0, last_used REAL)"
        )
        self.conn.commit()

    def request(self, req: KeyRequest) -> str:
        """自助申请：生成待审批 Key。"""

        key = "gw-" + secrets.token_hex(4)
        now = time.time()
        self.conn.execute(
            "INSERT INTO vkeys VALUES (?,?,?,?,?,?,?,?,?,?)",
            (key, req.owner, req.project, req.budget_usd, ",".join(req.allowed_models),
             "pending", now, now + req.ttl_days * 86400, 0.0, None),
        )
        self.conn.commit()
        return key

    def approve(self, key: str) -> bool:
        """运营审批：pending -> active。"""

        cur = self.conn.execute("UPDATE vkeys SET status='active' WHERE key=? AND status='pending'", (key,))
        self.conn.commit()
        return cur.rowcount == 1

    def record_spend(self, key: str, cost: float, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        self.conn.execute("UPDATE vkeys SET spent=spent+?, last_used=? WHERE key=?", (cost, now, key))
        self.conn.commit()

    def enforce(self, key: str, now: float | None = None) -> tuple[bool, str]:
        """调用前检查：状态 active + 未过期 + 未超预算。"""

        now = now if now is not None else time.time()
        row = self.conn.execute(
            "SELECT status, expires, budget, spent FROM vkeys WHERE key=?", (key,)
        ).fetchone()
        if not row:
            return False, "unknown key"
        status, expires, budget, spent = row
        if status != "active":
            return False, f"key {status}"
        if now > expires:
            return False, "expired"
        if spent >= budget:
            return False, "budget exceeded"
        return True, "ok"

    def review_idle(self, idle_days: int = 30, now: float | None = None) -> list[str]:
        """每月 review：找出闲置 Key（从未用或超 idle_days 未用）建议回收。"""

        now = now if now is not None else time.time()
        cutoff = now - idle_days * 86400
        rows = self.conn.execute("SELECT key, last_used FROM vkeys WHERE status='active'").fetchall()
        return [k for k, last in rows if last is None or last < cutoff]

    def reclaim(self, key: str) -> None:
        self.conn.execute("UPDATE vkeys SET status='reclaimed' WHERE key=?", (key,))
        self.conn.commit()


def main() -> None:
    panel = VirtualKeyPanel(db_path=":memory:")
    print("=== 虚拟 Key 治理面板 ===\n")

    # 1. 自助申请
    key = panel.request(KeyRequest("张三", "销售助手", budget_usd=500, allowed_models=["gpt-4o", "claude"], ttl_days=90))
    print(f"申请 Key：{key}（待审批）")
    print("未审批时调用：", panel.enforce(key))

    # 2. 运营审批
    panel.approve(key)
    print("审批后调用：", panel.enforce(key))

    # 3. 预算耗尽
    panel.record_spend(key, 500.0)
    print("花光预算后：", panel.enforce(key))

    # 4. 闲置回收 review
    now = time.time()
    idle_key = panel.request(KeyRequest("李四", "废弃实验", 100, ["claude"], ttl_days=90))
    panel.approve(idle_key)
    idle = panel.review_idle(idle_days=30, now=now + 40 * 86400)
    print(f"\n闲置回收 review（40 天后）：建议回收 {idle}")
    for k in idle:
        panel.reclaim(k)
    print("回收后状态：", panel.enforce(idle_key, now=now + 40 * 86400))


if __name__ == "__main__":
    main()
