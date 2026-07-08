"""State 四作用域完整用法 —— 工业级客服场景。

对应文章第二节"State 四作用域"里的 handle_customer_query 示例：
同一个工具同时操作 user 级偏好、app 级配额、session 级历史、temp 级临时值。

作用域回顾（key 前缀区分持久化目标）：
    无前缀   -> session.state      （本次对话）
    user:    -> session.user_state （同用户跨 session）
    app:     -> session.app_state  （全应用共享）
    temp:    -> 抛弃，不持久化      （仅当次执行）

本脚本用确定性 mock 的 ToolContext + 前缀分发存储复刻这套接口。
"""

from __future__ import annotations

import sys


class ScopedState:
    """按前缀把 state[key] 路由到四个持久化目标（extract_state_delta 的效果）。"""

    def __init__(self, session=None, user=None, app=None) -> None:
        self.session = dict(session or {})
        self.user = dict(user or {})
        self.app = dict(app or {})
        self.temp: dict = {}

    def _bucket(self, key: str):
        if key.startswith("user:"):
            return self.user, key[5:]
        if key.startswith("app:"):
            return self.app, key[4:]
        if key.startswith("temp:"):
            return self.temp, key[5:]
        return self.session, key

    def get(self, key, default=None):
        bucket, real = self._bucket(key)
        return bucket.get(real, default)

    def __setitem__(self, key, value):
        bucket, real = self._bucket(key)
        bucket[real] = value

    def __getitem__(self, key):
        return self.get(key)


class ToolContext:
    def __init__(self, state: ScopedState) -> None:
        self.state = state


try:  # google-adk 导入 try/except 保护
    from google.adk.tools import ToolContext as _Real  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


def compute_intermediate(query: str) -> str:
    return f"预处理({query})"


def process(query, user_lang, past_queries) -> dict:
    return {"answer": f"[{user_lang}] 已处理「{query}」，历史 {len(past_queries)} 条"}


def handle_customer_query(query: str, tool_context: ToolContext) -> dict:
    st = tool_context.state
    # 1. user 级（长期偏好）
    user_lang = st.get("user:language", "zh-CN")
    user_vip = st.get("user:vip_level", 0)
    # 2. app 级（全局配额）
    daily_quota = st.get("app:vip_quota_remaining", 1000)
    if user_vip > 0 and daily_quota <= 0:
        return {"error": "今日 VIP 配额用完"}
    # 3. session 级（本次对话）
    past = st.get("recent_queries", [])
    # 4. temp（不持久化）
    st["temp:scratch"] = compute_intermediate(query)
    # 5. 处理
    result = process(query, user_lang, past)
    # 6. 写回
    st["recent_queries"] = past + [query]
    if user_vip > 0:
        st["app:vip_quota_remaining"] = daily_quota - 1
    return result


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock ToolContext 演示四作用域用法。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    state = ScopedState(
        user={"language": "zh-CN", "vip_level": 1},
        app={"vip_quota_remaining": 2},
    )
    ctx = ToolContext(state)

    for i in range(1, 4):
        print(f"== 第 {i} 次查询 ==")
        r = handle_customer_query(f"问题{i}", ctx)
        print("   返回:", r)
        print("   session.recent_queries =", state.get("recent_queries"))
        print("   app:vip_quota_remaining =", state.get("app:vip_quota_remaining"))
        print("   temp:scratch =", state.get("temp:scratch"),
              "(下轮不会跨 invocation 保留，此处 mock 未清仅示意)")
        print()

    print("== 底层存储（前缀分发） ==")
    print("   user :", state.user)
    print("   app  :", state.app)
    print("   session:", state.session)
    print("\n结论：同一个 state[key] 接口，前缀自动区分四种持久化生命周期。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
