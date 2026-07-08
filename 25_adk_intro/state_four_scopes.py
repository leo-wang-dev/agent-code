"""4 作用域 State 完整 demo —— session / user: / app: / temp:。

对应文章第二节"Session + State —— 会话和状态"里的四作用域机制。

ADK 用 key 前缀区分持久化范围：
    无前缀   -> Session 级（一次对话）
    user:    -> User 级（同用户跨 session）
    app:     -> App 级（全应用共享）
    temp:    -> 仅当次 invocation（不持久化）

真实 ADK 里你在 tool 里这样写：
    tool_context.state["session_notes"] = "..."
    tool_context.state["user:language"] = "Chinese"
    tool_context.state["app:total_calls"] = 42
    tool_context.state["temp:scratch"] = "..."

本脚本用确定性 mock 复刻这套前缀分发逻辑：把一次写入按前缀路由到
不同的底层存储，并演示"跨 session 只有 user:/app: 存活、temp: 永不持久化"。
"""

from __future__ import annotations

import sys

try:  # google-adk 导入 try/except 保护
    from google.adk.sessions import InMemorySessionService  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


class ScopedStateStore:
    """按 key 前缀把 state 分发到四个持久化层次的 mock 实现。"""

    def __init__(self) -> None:
        self.app: dict[str, object] = {}          # 全 app 共享
        self.users: dict[str, dict] = {}          # user_id -> {}
        self.sessions: dict[str, dict] = {}        # session_id -> {}
        self.temp: dict[str, object] = {}          # 仅当次 invocation

    def _bucket_and_key(self, user_id: str, session_id: str, key: str):
        if key.startswith("user:"):
            return self.users.setdefault(user_id, {}), key[len("user:"):], "user"
        if key.startswith("app:"):
            return self.app, key[len("app:"):], "app"
        if key.startswith("temp:"):
            return self.temp, key[len("temp:"):], "temp"
        return self.sessions.setdefault(session_id, {}), key, "session"

    def set(self, user_id: str, session_id: str, key: str, value: object) -> str:
        bucket, real_key, scope = self._bucket_and_key(user_id, session_id, key)
        bucket[real_key] = value
        return scope

    def get(self, user_id: str, session_id: str, key: str):
        bucket, real_key, _ = self._bucket_and_key(user_id, session_id, key)
        return bucket.get(real_key)

    def end_invocation(self) -> None:
        """一次 invocation 结束：temp: 作用域清空（永不持久化）。"""
        self.temp.clear()


def dump_scope(title: str, data: dict) -> None:
    print(f"  {title}: {data if data else '（空）'}")


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示四作用域 State。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    store = ScopedStateStore()
    user_id = "user_123"

    # ---- Session A：一次 invocation 内写入四个作用域 ----
    print("== Session A：写入四作用域 ==")
    writes = {
        "session_notes": "用户在问退货政策",   # 无前缀 -> session
        "user:language": "Chinese",            # user: -> 跨 session
        "app:total_calls": 42,                 # app: -> 全应用
        "temp:scratch": "中间计算结果",          # temp: -> 不持久化
    }
    for key, value in writes.items():
        scope = store.set(user_id, "session_A", key, value)
        print(f"  写 {key!r:<22} -> [{scope}] 存储")

    print("\n  当次可读（invocation 内 temp: 仍可见）：")
    for key in writes:
        print(f"    {key!r:<22} = {store.get(user_id, 'session_A', key)!r}")

    # invocation 结束：temp 清空
    store.end_invocation()

    # ---- Session B：同一 user，新 session ----
    print("\n== Session B：同一 user 的新会话 —— 谁还活着？ ==")
    checks = ["session_notes", "user:language", "app:total_calls", "temp:scratch"]
    for key in checks:
        value = store.get(user_id, "session_B", key)
        alive = "存活" if value is not None else "已失效"
        print(f"    {key!r:<22} = {value!r:<18} [{alive}]")

    print("\n== 底层存储快照 ==")
    dump_scope("app  级", store.app)
    dump_scope("user 级(user_123)", store.users.get(user_id, {}))
    dump_scope("session_A", store.sessions.get("session_A", {}))
    dump_scope("session_B", store.sessions.get("session_B", {}))
    dump_scope("temp 级", store.temp)

    print("\n结论：session_notes 只在 A 可见；user:/app: 跨 session 存活；"
          "temp: invocation 结束即清空。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
