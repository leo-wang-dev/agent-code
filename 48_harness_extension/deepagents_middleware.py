"""DeepAgents 自定义 Middleware 完整实现 —— 共享知识库 / 集体洞察 / 隐私控制三层。

对应文章第 48 篇 七、反直觉的建议（用 DeepAgents SDK + 自己的 Middleware 替代 fork）。

DeepAgents 若已安装，`describe_real_wiring()` 展示真实 create_deep_agent 接线方式；
但可运行 demo 用**离线 mock 中间件链**（before_model / after_model 钩子），不构造真实
模型、不联网——符合"import 不发网络"。

离线可跑：`python3 deepagents_middleware.py`
"""

from __future__ import annotations

from dataclasses import dataclass, field

try:
    import deepagents  # noqa: F401

    _HAS_DEEPAGENTS = True
except Exception:  # pragma: no cover
    _HAS_DEEPAGENTS = False


# ---- 离线中间件协议：before_model 改 context / after_model 改 output ----

class Middleware:
    name = "base"

    def before_model(self, ctx: dict) -> dict:
        return ctx

    def after_model(self, ctx: dict, output: str) -> str:
        return output


class SharedKnowledgeBaseMiddleware(Middleware):
    """共享领域知识（全平台共享，非隐私）——注入到 context。"""

    name = "shared_kb"

    def __init__(self, kb: dict[str, str]):
        self.kb = kb

    def before_model(self, ctx: dict) -> dict:
        q = ctx.get("query", "")
        hit = next((v for k, v in self.kb.items() if k in q), None)
        if hit:
            ctx.setdefault("injected", []).append(f"[共享KB] {hit}")
        return ctx


class SharedInsightsMiddleware(Middleware):
    """集体洞察（跨用户匿名化聚合）——k-匿名，单条不可识别。"""

    name = "shared_insights"

    def __init__(self, insights: list[dict], k: int = 10):
        self.insights = insights
        self.k = k

    def before_model(self, ctx: dict) -> dict:
        # 只注入代表 >= k 个用户的聚合洞察（文章：k-匿名化）
        safe = [i["text"] for i in self.insights if i.get("cohort_size", 0) >= self.k]
        if safe:
            ctx.setdefault("injected", []).append(f"[集体洞察] {safe[0]}")
        return ctx


class PrivacyControlMiddleware(Middleware):
    """隐私控制——出站脱敏 + opt-in 校验（文章：默认不分享、可撤回）。"""

    name = "privacy"

    def __init__(self, user_opt_in: bool):
        self.user_opt_in = user_opt_in

    def before_model(self, ctx: dict) -> dict:
        # 未 opt-in 的用户，其私有数据不得进入可能被共享的通道
        if not self.user_opt_in:
            ctx["shareable"] = False
        return ctx

    def after_model(self, ctx: dict, output: str) -> str:
        import re
        return re.sub(r"1[3-9]\d{9}", "[手机号已脱敏]", output)


@dataclass
class MockDeepAgent:
    """离线 mock：按 middleware 链跑 before → model → after。"""

    tools: list[str]
    system_prompt: str
    middleware: list[Middleware] = field(default_factory=list)

    def invoke(self, query: str, user_opt_in: bool = False) -> dict:
        ctx: dict = {"query": query, "injected": [], "user_opt_in": user_opt_in}
        for mw in self.middleware:
            ctx = mw.before_model(ctx)

        # mock "模型"：把注入内容 + query 组织成回答
        injected = " ".join(ctx.get("injected", []))
        output = f"根据 {injected or '基础知识'} 回答「{query}」。联系电话 13800138000。"

        for mw in self.middleware:
            output = mw.after_model(ctx, output)
        return {"output": output, "context": ctx}


def build_beauty_agent(user_opt_in: bool = False) -> MockDeepAgent:
    """对齐文章代码形态：create_deep_agent(tools=..., system_prompt=..., middleware=[...])。"""
    return MockDeepAgent(
        tools=["search_kb", "ingredient_lookup", "product_db"],
        system_prompt="你是美容助手...",
        middleware=[
            SharedKnowledgeBaseMiddleware(kb={"视黄醇": "视黄醇需建立耐受、夜间使用、注意防晒"}),
            SharedInsightsMiddleware(insights=[{"text": "同类敏感肌用户多从低浓度起步", "cohort_size": 42}]),
            PrivacyControlMiddleware(user_opt_in=user_opt_in),
        ],
    )


def describe_real_wiring() -> str:
    """真实 DeepAgents 接线方式（不实际构造模型，避免联网）。"""
    return (
        "from deepagents import create_deep_agent\n"
        "agent = create_deep_agent(\n"
        "    tools=[search_kb, ingredient_lookup, product_db],\n"
        "    system_prompt='你是美容助手...',\n"
        "    middleware=[SharedKnowledgeBaseMiddleware(...), SharedInsightsMiddleware(...), PrivacyControlMiddleware(...)],\n"
        ")\n"
    )


def _demo() -> None:
    print(f"deepagents 已安装: {_HAS_DEEPAGENTS}")
    if _HAS_DEEPAGENTS:
        print("真实接线方式（教学，不实际构造模型/联网）：\n")
        print(describe_real_wiring())

    print("=== 离线 middleware 链演示 ===")
    agent = build_beauty_agent(user_opt_in=False)
    result = agent.invoke("我想用视黄醇但我是敏感肌")
    print("  注入内容:", result["context"]["injected"])
    print("  是否可共享:", result["context"].get("shareable"))
    print("  输出(已脱敏):", result["output"])


if __name__ == "__main__":
    _demo()
