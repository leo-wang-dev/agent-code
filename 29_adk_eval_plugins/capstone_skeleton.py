"""ADK Capstone 项目骨架 —— 企业级采购助手（9 个 phase 能力协同）。

对应文章第三节"ADK Capstone"。

这是一个**结构骨架 + 端到端 dry-run**：不接真实 LLM / GCP，用确定性 mock
把文章描述的 procurement_assistant 结构跑一遍，展示 9 个 phase 能力如何协同：
    Plugins(全局) -> Orchestrator(Delegation) -> 意图子流程
    级联搜索(catalog -> supplier -> web，仅在不够时升级 tier)
    Services(Session/Artifact/Memory) + Evaluation(CI)

真实工程里每个 Agent 是 LlmAgent、每个 Plugin 继承 google.adk.plugins.Plugin。
本骨架用 print + mock 呈现装配关系，可作为真实项目的填充起点。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.agents import LlmAgent  # noqa: F401
    from google.adk.app import App  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class Ctx:
    state: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    def emit(self, author: str, msg: str) -> None:
        self.events.append((author, msg))


# ---- Phase 08: 全局 Plugin（简化占位） ----
PLUGINS = ["LoggingPlugin", "SafetyPlugin", "CostTrackerPlugin", "MetricsPlugin"]


# ---- Phase 03: 级联搜索（Loop + 渐进 tier，成本/延迟递增，够了就停） ----
def cascade_search(need: str, ctx: Ctx) -> str:
    tiers = [
        ("catalog_search_agent", "自家产品库", need in ("常规办公用品",)),
        ("supplier_search_agent", "供应商库", need in ("常规办公用品", "定制设备")),
        ("web_search_agent", "全网", True),
    ]
    for agent, source, hit in tiers:
        ctx.emit(agent, f"在{source}搜索 {need}")
        if hit:
            ctx.emit(agent, f"命中 -> 停止级联（未升级到更贵的 tier）")
            return f"{source}命中"
    return "全网兜底"


# ---- Phase 06: State 四作用域 ----
def load_user_context(ctx: Ctx) -> None:
    ctx.state["user:role"] = "采购专员"          # user 级
    ctx.state["app:total_requests"] = ctx.state.get("app:total_requests", 0) + 1  # app 级
    ctx.emit("orchestrator", f"加载用户上下文 role={ctx.state['user:role']}")


# ---- Phase 05: 自建 Skills 模式（非 ADK 原生）渐进加载 ----
QUOTE_SKILLS = ["议价", "合规", "物流", "税务", "合同"]


def quote_generation(need: str, ctx: Ctx) -> str:
    # 渐进加载：只激活与本需求相关的 skill
    active = ["合规", "合同"] if need == "定制设备" else ["议价", "合同"]
    ctx.state["active_skills"] = active
    ctx.emit("quote_generation_agent", f"渐进加载 skills={active}（共 {len(QUOTE_SKILLS)} 个可选）")
    return f"报价单（基于 {'+'.join(active)}）"


# ---- Phase 03: Orchestrator Delegation ----
def classify_intent(message: str) -> str:
    if "采购" in message or "买" in message:
        return "procure"
    if "报价" in message:
        return "quote"
    return "qa"


def orchestrate(message: str, ctx: Ctx) -> str:
    load_user_context(ctx)
    intent = classify_intent(message)
    ctx.emit("intent_classifier", f"意图 = {intent}")
    if intent == "procure":
        need = "定制设备" if "定制" in message else "常规办公用品"
        ctx.emit("requirements_collector", f"收集需求 -> {need}")
        search_result = cascade_search(need, ctx)
        quote = quote_generation(need, ctx)
        # Phase 04 Artifacts：保存版本化报价单
        ctx.state.setdefault("artifacts", {})["quote.md"] = 0
        ctx.emit("report_tool", "save_artifact('quote.md', v0)")
        return f"{search_result} -> {quote}"
    return "转 qa_agent 处理"


def print_architecture() -> None:
    print("[App: procurement_assistant]")
    print("  Plugins:", ", ".join(PLUGINS))
    print("  Root Agent: orchestrator (Delegation)")
    print("    sub_agents: intent_classifier / requirements_collector /")
    print("                cascade_search(Loop) / quote_generation / qa_agent")
    print("  Services: DatabaseSessionService / FileArtifactService / VertexAiMemoryService")
    print("  Evaluation: 50+ .test.json, 每日 CI 跑 trajectory + faithfulness + composite")


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 跑 Capstone 骨架 dry-run。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    print("== 架构总览 ==")
    print_architecture()

    print("\n== 端到端 dry-run：'帮我采购一批定制设备' ==")
    ctx = Ctx()
    result = orchestrate("帮我采购一批定制设备", ctx)
    for author, msg in ctx.events:
        print(f"  [{author}] {msg}")
    print("  => 结果:", result)
    print("  最终 state:", {k: v for k, v in ctx.state.items()})

    print("\n== 9 个 Phase 协同 ==")
    phases = [
        "01 概念: Agent/Tool 基础", "02 骨架: 标准目录", "03 编排: Delegation+级联Loop",
        "04 工具: FunctionTool+Artifacts", "05 Skills(自建): 渐进加载",
        "06 Memory: State 四作用域", "07 Eval: CI 集成", "08 Plugins: 全局横切",
        "09 Capstone: 全部协同",
    ]
    for p in phases:
        print("  -", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
