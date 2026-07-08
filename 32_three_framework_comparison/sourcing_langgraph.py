"""采购助手 —— LangGraph 版（工程派：显式状态机 + 节点级 Checkpoint + interrupt HITL）。

对应文章第 32 篇「二、LangGraph 版本」。

优先用真 langgraph；缺依赖回退到系列自研的纯 Python StateGraph（agent_examples.graph），
保证任何机器都能跑出同一条流程：

    python3 32_three_framework_comparison/sourcing_langgraph.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sourcing_common as sc  # noqa: E402


class SourcingState(TypedDict, total=False):
    """LangGraph 显式 State（TypedDict）—— 工程派的招牌：状态结构一目了然。"""

    query: str
    intent: str
    requirements: dict
    results: list
    ranked: list
    report: dict


def run(query: str = sc.DEFAULT_QUERY) -> sc.SourcingResult:
    trace: list[str] = []
    used_real = False

    def classify(state: dict) -> dict:
        return {"intent": sc.classify_intent(state["query"])}

    def collect(state: dict) -> dict:
        return {"requirements": sc.collect_requirements(state["query"])}

    def search(state: dict) -> dict:
        out = sc.cascade_search(state["requirements"])
        trace.extend(out["cascade_trace"])
        return {"results": out["results"]}

    def rerank(state: dict) -> dict:
        return {"ranked": sc.rerank_and_merge(state["results"])}

    def report(state: dict) -> dict:
        return {"report": sc.build_report(state["ranked"], state["requirements"])}

    try:
        from langgraph.graph import END, START, StateGraph

        used_real = True
        graph = StateGraph(SourcingState)
        graph.add_node("classify", classify)
        graph.add_node("collect", collect)
        graph.add_node("search", search)
        graph.add_node("rerank", rerank)
        graph.add_node("report", report)
        graph.add_edge(START, "classify")
        for a, b in [("classify", "collect"), ("collect", "search"), ("search", "rerank"), ("rerank", "report")]:
            graph.add_edge(a, b)
        graph.add_edge("report", END)
        app = graph.compile()  # 生产可传 checkpointer=PostgresSaver(...) 得节点级持久化
        final = app.invoke({"query": query})
    except ImportError:
        # 回退：系列自研纯 Python StateGraph（同样是显式节点 + 边）。
        from agent_examples.graph import StateGraph as MiniGraph

        g = MiniGraph()
        g.add_node("classify", classify)
        g.add_node("collect", collect)
        g.add_node("search", search)
        g.add_node("rerank", rerank)
        g.add_node("report", report)
        g.add_edge("START", "classify")
        for a, b in [("classify", "collect"), ("collect", "search"), ("search", "rerank"), ("rerank", "report")]:
            g.add_edge(a, b)
        g.add_edge("report", "END")
        final = g.compile().invoke({"query": query}, thread_id="ch32-lg")

    # HITL：需要审批时 LangGraph 用 interrupt() 在 report 后暂停（此处记录暂停点）。
    if final["report"]["needs_approval"]:
        trace.append("interrupt() 暂停等待经理审批（HITL）")

    return sc.SourcingResult(
        framework="LangGraph",
        intent=final["intent"],
        requirements=final["requirements"],
        ranked=final["ranked"],
        report=final["report"],
        trace=trace,
        used_real_lib=used_real,
    )


def main() -> None:
    result = run()
    print(f"=== LangGraph 版（真实库={result.used_real_lib}）===")
    print(result.report["artifact"])
    print("\n级联/HITL 轨迹：", result.trace)


if __name__ == "__main__":
    main()
