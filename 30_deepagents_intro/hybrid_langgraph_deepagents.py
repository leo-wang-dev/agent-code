"""LangGraph + DeepAgents 混合使用示例。

对应文章第 30 篇「五、工程上的混合使用」：
    [LangGraph 主流程] 确定性骨架：提交 -> 待审核 -> 待支付 -> 已支付
        └── "审核理由生成" 这个开放式子任务，包一个 DeepAgents Harness

设计原则：
  - 确定性流程（审批流）用 LangGraph 写死 —— 可持久化、可 HITL、可审计。
  - 开放式子任务（步骤数不确定）交给 Harness —— 自动做研究、写理由、自我审查。

两个库都用 try/except 保护；缺任一都回退到纯 Python 模拟（复用手搓 Harness），
保证任何机器都能跑出同样的流程演示：

    python3 30_deepagents_intro/hybrid_langgraph_deepagents.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from handwritten_harness import SubAgent, create_deep_agent  # noqa: E402


def _run_open_subtask_with_deepagents(reason_hint: str) -> str:
    """开放式子任务：生成审核理由。优先真 DeepAgents，缺依赖回退手搓 Harness。"""

    try:
        from deepagents import create_deep_agent as sdk_create_deep_agent
    except ImportError:
        # 回退：用手搓 Harness 跑同样的「研究->写理由->自审」流程。
        reviewer = SubAgent(
            name="reviewer",
            description="审核理由生成子 Agent",
            system_prompt="根据报销信息生成审核理由并自我复核。",
            runner=lambda text: f"审核理由：{text} 金额合规、票据齐全，建议通过。",
        )
        agent = create_deep_agent(subagents=[reviewer])
        result = agent.invoke(f"为这笔报销生成审核理由：{reason_hint}")
        return result["answer"] or f"[手搓Harness] 审核理由已生成（{reason_hint}）"

    # 有真 SDK：仅演示组装（真实调用需 ANTHROPIC_API_KEY）。
    import os

    def search_policy(query: str) -> str:
        """检索报销政策条款（占位工具，真实项目换成知识库检索）。"""

        return f"检索报销政策：{query}"

    agent = sdk_create_deep_agent(
        tools=[search_policy],
        system_prompt="你负责生成报销审核理由，先研究政策，再写理由，最后自审。",
    )
    if not os.getenv("ANTHROPIC_API_KEY"):
        return f"[DeepAgents 已装配，未设 key] 审核理由待生成（{reason_hint}）"
    out = agent.invoke({"messages": [{"role": "user", "content": f"生成审核理由：{reason_hint}"}]})
    return getattr(out["messages"][-1], "content", str(out["messages"][-1]))


# ---------------------------------------------------------------------------
# LangGraph 主流程（确定性审批骨架）
# ---------------------------------------------------------------------------

STATES = ["提交", "待审核", "待支付", "已支付"]


def _build_langgraph_flow():
    """优先用真 LangGraph 构图；缺依赖回退到显式状态机模拟。"""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return None  # 交给 _run_with_plain_state_machine

    graph = StateGraph(dict)

    def submit(state: dict) -> dict:
        return {**state, "status": "待审核"}

    def review(state: dict) -> dict:
        reason = _run_open_subtask_with_deepagents(state["expense"])
        return {**state, "status": "待支付", "review_reason": reason}

    def pay(state: dict) -> dict:
        return {**state, "status": "已支付"}

    graph.add_node("submit", submit)
    graph.add_node("review", review)
    graph.add_node("pay", pay)
    graph.add_edge(START, "submit")
    graph.add_edge("submit", "review")
    graph.add_edge("review", "pay")
    graph.add_edge("pay", END)
    return graph.compile()


def _run_with_plain_state_machine(expense: str) -> dict:
    """LangGraph 缺失时的等价确定性状态机。"""

    state = {"expense": expense, "status": "提交"}
    state["status"] = "待审核"
    state["review_reason"] = _run_open_subtask_with_deepagents(expense)
    state["status"] = "待支付"
    state["status"] = "已支付"
    return state


def main() -> None:
    expense = "差旅报销 1280 元（高铁 + 住宿）"
    app = _build_langgraph_flow()
    if app is None:
        print("未安装 langgraph（pip install langgraph），回退纯 Python 状态机。\n")
        final = _run_with_plain_state_machine(expense)
    else:
        print("使用真实 LangGraph 主流程。\n")
        final = app.invoke({"expense": expense, "status": "提交"})

    print("=== 混合架构执行结果 ===")
    print("确定性骨架状态流：", " -> ".join(STATES))
    print("最终状态：", final["status"])
    print("开放式子任务产出（审核理由）：")
    print("  ", final.get("review_reason"))
    print("\n要点：骨架状态由 LangGraph 保证确定性，理由生成由 Harness 保证智能。")


if __name__ == "__main__":
    main()
