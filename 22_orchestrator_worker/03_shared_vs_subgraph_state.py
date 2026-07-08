"""共享 State vs 子图 State 对照 —— Worker 内部要不要有自己的 State？

共享 State：主图和所有 Worker 共享同一个 TypedDict。
  优势：简单、数据集中、调试方便；劣势：Worker 之间字段污染风险。
子图 State：每个 Worker 用 Subgraph，子图有独立 State，只把最终输出暴露给主图。
  优势：内部细节字段完全隔离；代价：多一层 schema。

生产经验：项目开始用共享 State，复杂度上升再重构成子图 State，别一开始就过度设计。

需要依赖：pip install langgraph
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph")
    print("（本示例演示共享 State vs 子图 State，缺少 langgraph 无法运行）")
    raise SystemExit(0)


# ==================== 方案 A：共享 State ====================
class TeamStateShared(TypedDict, total=False):
    user_query: str
    research_result: str  # research worker 直接写主 State 字段


def research_worker_shared(state: TeamStateShared) -> dict:
    # 内部中间字段也只能塞进主 State（可能污染）
    return {"research_result": f"[shared] 关于「{state['user_query']}」的调研结论"}


def build_shared_app():
    graph = StateGraph(TeamStateShared)
    graph.add_node("research", research_worker_shared)
    graph.add_edge(START, "research")
    graph.add_edge("research", END)
    return graph.compile()


# ==================== 方案 B：子图 State ====================
class ResearchState(TypedDict, total=False):
    query: str
    sources: list          # 子图内部细节
    internal_steps: list   # 子图内部细节
    summary: str           # 子图最终输出


def research_collect(state: ResearchState) -> dict:
    return {"sources": ["src1", "src2"], "internal_steps": ["搜索", "去重"]}


def research_summarize(state: ResearchState) -> dict:
    return {"summary": f"[subgraph] 基于 {len(state['sources'])} 个来源的结论"}


def build_research_subgraph():
    g = StateGraph(ResearchState)
    g.add_node("collect", research_collect)
    g.add_node("summarize", research_summarize)
    g.add_edge(START, "collect")
    g.add_edge("collect", "summarize")
    g.add_edge("summarize", END)
    return g.compile()


class TeamStateSub(TypedDict, total=False):
    user_query: str
    research_summary: str  # 只暴露子图最终输出，内部 sources/internal_steps 被隔离


def research_worker_sub(state: TeamStateSub) -> dict:
    sub = build_research_subgraph()
    out = sub.invoke({"query": state["user_query"]})
    # 只把子图的 summary 暴露给主图，内部字段不外泄
    return {"research_summary": out["summary"]}


def build_sub_app():
    graph = StateGraph(TeamStateSub)
    graph.add_node("research", research_worker_sub)
    graph.add_edge(START, "research")
    graph.add_edge("research", END)
    return graph.compile()


def main() -> None:
    q = "新能源电池"
    shared = build_shared_app().invoke({"user_query": q})
    print("共享 State 结果字段：", list(shared.keys()))
    print("  →", shared["research_result"])

    sub = build_sub_app().invoke({"user_query": q})
    print("子图 State 主图字段：", list(sub.keys()), "（子图内部 sources/internal_steps 已隔离）")
    print("  →", sub["research_summary"])


if __name__ == "__main__":
    main()
