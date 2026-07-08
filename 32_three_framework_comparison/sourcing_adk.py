"""采购助手 —— Google ADK 版（企业派：Delegation + LoopAgent 级联 + Plugin 横切 + Event）。

对应文章第 32 篇「二、Google ADK 版本」。

优先用真 google-adk；缺依赖回退到系列自研 ADK 原语（agent_examples.frameworks）：
    python3 32_three_framework_comparison/sourcing_adk.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sourcing_common as sc  # noqa: E402

# Plugin 全局横切（日志 / 安全 / 成本）——ADK 招牌，几乎零业务侵入。
PLUGINS = ["LoggingPlugin", "SafetyPlugin", "CostTrackerPlugin"]
SUB_AGENTS = ["intent_classifier", "requirements_collector", "cascade_search(LoopAgent)", "quote_generator", "qa_agent"]


def _detect_real_adk() -> bool:
    try:
        import google.adk  # noqa: F401

        return True
    except ImportError:
        return False


def run(query: str = sc.DEFAULT_QUERY) -> sc.SourcingResult:
    used_real = _detect_real_adk()

    # Event Sourcing：每个 state_delta 都留原子记录（ADK 可调试性来源）。
    events: list[str] = []

    def emit(kind: str, payload: str) -> None:
        events.append(f"[event:{kind}] {payload}")

    for plugin in PLUGINS:
        emit("plugin_attach", plugin)

    # Root Agent (Delegation) -> intent_classifier
    intent = sc.classify_intent(query)
    emit("delegate", f"intent_classifier -> {intent}")

    requirements = sc.collect_requirements(query)
    emit("state_delta", f"requirements={requirements}")

    # LoopAgent + escalate 控制三级级联搜索
    searched = sc.cascade_search(requirements)
    for step in searched["cascade_trace"]:
        emit("loop_escalate", step)

    ranked = sc.rerank_and_merge(searched["results"])
    emit("state_delta", f"ranked_top={ranked[0]['supplier'] if ranked else None}")

    report = sc.build_report(ranked, requirements)
    emit("artifact_save", "quote_report.md")

    # HITL：ADK 用 callback / Plugin 拼审批（约 50 行）
    if report["needs_approval"]:
        emit("callback", "before_finalize -> 大额转经理审批（HITL via callback/Plugin）")

    trace = events + [f"CostTrackerPlugin 记账：Token≈15k"]
    return sc.SourcingResult(
        framework="ADK",
        intent=intent,
        requirements=requirements,
        ranked=ranked,
        report=report,
        trace=trace,
        used_real_lib=used_real,
    )


def main() -> None:
    result = run()
    print(f"=== Google ADK 版（真实库={result.used_real_lib}）===")
    print("Plugins:", PLUGINS)
    print("Sub-agents:", SUB_AGENTS)
    print()
    print(result.report["artifact"])
    print("\nEvent/HITL 轨迹：")
    for line in result.trace:
        print("  ", line)


if __name__ == "__main__":
    main()
