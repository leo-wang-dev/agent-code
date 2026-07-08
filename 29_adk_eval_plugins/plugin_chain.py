"""生产级 Plugin 链（8 个 Plugin）+ Plugin vs Callback 协作顺序。

对应文章第二节"Plugin 系统"。

Plugin 是 Callback 的全局升级版：一处定义、全 App 所有 Agent 生效。
执行顺序：Plugin 链先于 Agent 自己的 Callback；Plugin 返回非 None 即短路。

真实 ADK 写法：
    from google.adk.plugins import Plugin
    class LoggingPlugin(Plugin):
        async def before_tool_async(self, tool_name, tool_args, tool_context): ...
    app = App(name="my_app", root_agent=root_agent,
              plugins=[LoggingPlugin(), CostTrackerPlugin(), SafetyPlugin()])

本脚本用确定性 mock 复刻 8 个 Plugin 的生产链 + Plugin/Callback 执行顺序。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.plugins import Plugin as _Real  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class Ctx:
    state: dict = field(default_factory=dict)
    log: list = field(default_factory=list)


class Plugin:
    """mock 基类：三时机默认放行（返回 None）。"""

    name = "plugin"

    def before_model(self, model_input: str, ctx: Ctx):
        return None

    def before_tool(self, tool_name: str, tool_args: dict, ctx: Ctx):
        return None

    def after_model(self, response: dict, ctx: Ctx):
        return None


# ---- 8 个生产 Plugin ----
class LoggingPlugin(Plugin):
    name = "LoggingPlugin"

    def before_tool(self, tool_name, tool_args, ctx):
        ctx.log.append(f"[log] tool={tool_name} args={tool_args}")
        return None


class SafetyPlugin(Plugin):
    name = "SafetyPlugin"
    SENSITIVE = ("身份证", "银行卡")

    def before_model(self, model_input, ctx):
        if any(s in model_input for s in self.SENSITIVE):
            return {"content": "请求含敏感内容，已拦截。"}  # 短路
        return None


class InjectionDetectionPlugin(Plugin):
    name = "InjectionDetectionPlugin"

    def before_model(self, model_input, ctx):
        if "ignore previous instructions" in model_input.lower():
            return {"content": "检测到注入，已拦截。"}
        return None


class CostTrackerPlugin(Plugin):
    name = "CostTrackerPlugin"

    def __init__(self, daily_budget_usd: float = 100) -> None:
        self.daily_budget = daily_budget_usd

    def after_model(self, response, ctx):
        cost = response.get("total_tokens", 0) * 0.000005
        ctx.state["app:total_cost"] = round(ctx.state.get("app:total_cost", 0) + cost, 6)
        return None


class RateLimitPlugin(Plugin):
    name = "RateLimitPlugin"

    def __init__(self, qps: int = 10) -> None:
        self.qps = qps

    def before_model(self, model_input, ctx):
        n = ctx.state.get("app:req_count", 0) + 1
        ctx.state["app:req_count"] = n
        if n > self.qps:
            return {"content": "限流：请求过于频繁。"}
        return None


class MetricsPlugin(Plugin):
    name = "MetricsPlugin"

    def after_model(self, response, ctx):
        ctx.state["app:model_calls"] = ctx.state.get("app:model_calls", 0) + 1
        return None


class TracingPlugin(Plugin):
    name = "TracingPlugin"

    def before_tool(self, tool_name, tool_args, ctx):
        ctx.log.append(f"[trace] span open: {tool_name}")
        return None


class UserContextPlugin(Plugin):
    name = "UserContextPlugin"

    def before_model(self, model_input, ctx):
        ctx.state.setdefault("user:id", "u1")  # 自动注入用户身份
        return None


# ---- mock App：Plugin 链 + Agent Callback ----
class App:
    def __init__(self, plugins: list, agent_callbacks: dict | None = None) -> None:
        self.plugins = plugins
        self.agent_callbacks = agent_callbacks or {}

    def before_model(self, model_input: str, ctx: Ctx):
        for p in self.plugins:  # Plugin 链先跑
            short = p.before_model(model_input, ctx)
            if short is not None:
                ctx.log.append(f"[SHORT] {p.name} 短路 -> 跳过后续 Plugin 和 Agent Callback")
                return short
        cb = self.agent_callbacks.get("before_model")  # 再跑 Agent 自己的 Callback
        if cb:
            return cb(model_input, ctx)
        return None

    def before_tool(self, tool_name, tool_args, ctx: Ctx):
        for p in self.plugins:
            if p.before_tool(tool_name, tool_args, ctx) is not None:
                return "short"
        return None

    def after_model(self, response, ctx: Ctx):
        for p in self.plugins:
            p.after_model(response, ctx)


def build_app() -> App:
    return App(plugins=[
        LoggingPlugin(),                                   # 1 审计
        SafetyPlugin(), InjectionDetectionPlugin(),        # 2 安全
        CostTrackerPlugin(daily_budget_usd=100), RateLimitPlugin(qps=10),  # 3 成本
        MetricsPlugin(), TracingPlugin(),                  # 4 可观测
        UserContextPlugin(),                               # 5 业务通用
    ])


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 复刻 8-Plugin 生产链。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    app = build_app()
    print("== 生产 Plugin 链（8 个，全 App 生效） ==")
    for i, p in enumerate(app.plugins, 1):
        print(f"   {i}. {p.name}")

    ctx = Ctx()

    print("\n== 正常请求 ==")
    app.before_model("帮我查一下 ADK 的资料", ctx)
    app.before_tool("search_web", {"query": "ADK"}, ctx)
    app.after_model({"total_tokens": 1000}, ctx)
    for line in ctx.log:
        print("  ", line)
    print("   state:", ctx.state)

    print("\n== 敏感请求（SafetyPlugin 短路） ==")
    ctx2 = Ctx()
    blocked = app.before_model("帮我查身份证信息", ctx2)
    print("   before_model ->", blocked)
    print("   log:", ctx2.log)

    print("\n== Plugin vs Callback ==")
    print("   范围: Plugin=全 App，Callback=单 Agent")
    print("   顺序: Plugin 链先于 Agent Callback；Plugin 返回非 None 即短路")
    return 0


if __name__ == "__main__":
    sys.exit(main())
