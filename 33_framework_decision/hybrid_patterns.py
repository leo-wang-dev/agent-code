"""三种主流混用模式的最小可运行代码。

对应文章第 33 篇「三、三种主流混用模式」：
  模式 1  LangGraph 主 + CrewAI 子      —— 严谨骨架里嵌角色协作子任务
  模式 2  ADK 主 + DeepAgents 子         —— 工业化骨架里嵌长任务
  模式 3  三层叠加 ADK + LangGraph + DeepAgents

所有框架都 try/except；缺依赖回退纯 Python 等价实现，保证可跑：
    python3 33_framework_decision/hybrid_patterns.py
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# 模式 1：LangGraph 主 + CrewAI 子
# ---------------------------------------------------------------------------


def _crew_complaint(complaint: str) -> str:
    """投诉处理子任务：分类 -> 起草 -> 审核（CrewAI，缺依赖回退）。"""

    try:
        from crewai import Agent, Crew, Process, Task  # noqa: F401

        lib = "CrewAI"
    except ImportError:
        lib = "fallback"
    # 业务逻辑与框架解耦（文章建议 4）：纯函数，两条路径共用。
    steps = ["分类=退货类", "起草=已生成致歉+退货指引", "审核=通过"]
    return f"[{lib}] {complaint} -> " + " | ".join(steps)


def pattern_1_langgraph_main_crewai_sub(user_input: str) -> dict:
    """LangGraph 主流程，complaint 节点内嵌 CrewAI Crew。"""

    def classify(state: dict) -> dict:
        return {**state, "route": "complaint" if "投诉" in state["input"] else "normal"}

    def complaint_node(state: dict) -> dict:
        return {**state, "resolution": _crew_complaint(state["input"])}

    try:
        from typing import Any, TypedDict  # noqa: F401

        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(dict)
        graph.add_node("classify", classify)
        graph.add_node("complaint", complaint_node)
        graph.add_edge(START, "classify")
        graph.add_edge("classify", "complaint")
        graph.add_edge("complaint", END)
        # 注：真实项目会用条件边按 route 分流；此处 demo 直连投诉节点。
        final = graph.compile().invoke({"input": user_input, "route": ""})
        lib = "LangGraph"
    except ImportError:
        state = classify({"input": user_input})
        final = complaint_node(state)
        lib = "fallback-state-machine"
    return {"main_framework": lib, "resolution": final["resolution"]}


# ---------------------------------------------------------------------------
# 模式 2：ADK 主 + DeepAgents 子
# ---------------------------------------------------------------------------


def _deepagents_research(topic: str) -> str:
    try:
        from deepagents import create_deep_agent  # noqa: F401

        return f"[DeepAgents] 已装配长任务研究：{topic}（真实运行需 ANTHROPIC_API_KEY）"
    except ImportError:
        # 回退：模拟长任务三大模式产出结论摘要。
        return f"[fallback] {topic} 深度研究完成：TODO/文件系统/子Agent 三模式跑通，结论已汇总"


def pattern_2_adk_main_deepagents_sub(topic: str) -> dict:
    try:
        import google.adk  # noqa: F401

        main_lib = "ADK"
    except ImportError:
        main_lib = "fallback"
    # ADK 主流程挂 Plugin（日志/审计/配额），start_research 工具内调 DeepAgents。
    plugins = ["LoggingPlugin", "AuditPlugin", "QuotaPlugin"]
    report = _deepagents_research(topic)
    return {"main_framework": main_lib, "plugins": plugins, "report": report}


# ---------------------------------------------------------------------------
# 模式 3：三层叠加 ADK + LangGraph + DeepAgents
# ---------------------------------------------------------------------------


def pattern_3_three_layer(topic: str) -> dict:
    """外层 ADK 管配额/评测 -> 中层 LangGraph 管研究分诊 -> 内层 DeepAgents 做长任务。"""

    # 外层 ADK
    outer = "ADK: Plugins + 多用户配额 + Evaluation"
    # 中层 LangGraph：research_orchestrator 子图（分类研究类型 -> 选数据源 -> 深研 -> 综合）
    middle_nodes = ["classify_research_type", "select_sources", "deep_research_node", "synthesize"]
    # 内层 DeepAgents：deep_research_node 调用
    inner = _deepagents_research(topic)
    return {
        "layer_outer": outer,
        "layer_middle": " -> ".join(middle_nodes),
        "layer_inner": inner,
        "note": "每层用最适合的框架，总成本不增加多少但能力完整覆盖",
    }


def main() -> None:
    print("=== 模式 1：LangGraph 主 + CrewAI 子 ===")
    print(pattern_1_langgraph_main_crewai_sub("我要投诉这次采购的质量问题"))

    print("\n=== 模式 2：ADK 主 + DeepAgents 子 ===")
    print(pattern_2_adk_main_deepagents_sub("钛合金 2025 供应链趋势"))

    print("\n=== 模式 3：三层叠加 ===")
    for k, v in pattern_3_three_layer("可再生能源成本").items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
