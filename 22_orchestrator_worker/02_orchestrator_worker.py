"""Orchestrator-Worker 多 Agent 完整实现。

[用户输入] → [Orchestrator: 决定派哪些 Worker]
          → 并行 fan-out → [research] [pricing] [compliance]
          → fan-in → [Aggregator: 整合结果] → END

关键工程点：
  ① Worker 内部判断"是否被选中"，没选中直接返回 {}
  ② Orchestrator 连到多个 Worker → 自动并行 fan-out
  ③ 多个 Worker 连到 aggregator → fan-in（等全部完成）
  ④ worker_trace 用 Annotated[list, operator.add] 自动累加

Orchestrator 用 mock 的 call_llm（无需密钥）；真实场景用小模型决策、Worker 用大模型干活。

需要依赖：pip install langgraph
"""
from __future__ import annotations

import json
import operator
from typing import Annotated, TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph")
    print("（本示例演示 Orchestrator-Worker，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class TeamState(TypedDict, total=False):
    user_query: str
    research_result: str
    pricing_result: str
    compliance_result: str
    selected_workers: list
    final_answer: str
    worker_trace: Annotated[list, operator.add]  # 每个 Worker 各写一条，自动累加


# ---------- mock LLM：真实场景由小模型决策 ----------
def call_llm(prompt: str) -> str:
    query = prompt.lower()
    workers = []
    if "调研" in prompt or "资料" in prompt or "了解" in prompt:
        workers.append("research")
    if "报价" in prompt or "价格" in prompt or "多少钱" in prompt:
        workers.append("pricing")
    if "合规" in prompt or "合法" in prompt or "审查" in prompt:
        workers.append("compliance")
    if not workers:
        workers = ["research"]
    return json.dumps({"workers": workers})


def orchestrator(state: TeamState) -> dict:
    prompt = f"分析用户请求，决定派遣哪些 Agent（research/pricing/compliance）：{state['user_query']}"
    decision = call_llm(prompt)
    return {"selected_workers": json.loads(decision)["workers"]}


def research_worker(state: TeamState) -> dict:
    if "research" not in state["selected_workers"]:
        return {}  # 不该派的 Worker 直接跳过
    return {"research_result": "市场调研结论：需求旺盛",
            "worker_trace": [{"worker": "research", "status": "done"}]}


def pricing_worker(state: TeamState) -> dict:
    if "pricing" not in state["selected_workers"]:
        return {}
    return {"pricing_result": "报价 ¥128,000",
            "worker_trace": [{"worker": "pricing", "status": "done"}]}


def compliance_worker(state: TeamState) -> dict:
    if "compliance" not in state["selected_workers"]:
        return {}
    return {"compliance_result": "合规审查通过",
            "worker_trace": [{"worker": "compliance", "status": "done"}]}


def aggregator(state: TeamState) -> dict:
    parts = []
    if state.get("research_result"):
        parts.append(f"调研：{state['research_result']}")
    if state.get("pricing_result"):
        parts.append(f"报价：{state['pricing_result']}")
    if state.get("compliance_result"):
        parts.append(f"合规：{state['compliance_result']}")
    return {"final_answer": call_llm_summary("\n".join(parts))}


def call_llm_summary(summary: str) -> str:
    return f"综合回复：\n{summary}"


def build_app():
    graph = StateGraph(TeamState)
    graph.add_node("orchestrator", orchestrator)
    graph.add_node("research", research_worker)
    graph.add_node("pricing", pricing_worker)
    graph.add_node("compliance", compliance_worker)
    graph.add_node("aggregator", aggregator)

    graph.add_edge(START, "orchestrator")
    for w in ("research", "pricing", "compliance"):
        graph.add_edge("orchestrator", w)   # fan-out（自动并行）
        graph.add_edge(w, "aggregator")     # fan-in（等全部完成）
    graph.add_edge("aggregator", END)
    return graph.compile()


def main() -> None:
    app = build_app()
    result = app.invoke({"user_query": "帮我调研一下这个产品，顺便给个报价", "worker_trace": []})
    print("Orchestrator 选中的 Worker：", result["selected_workers"])
    print("Worker 执行轨迹：", result["worker_trace"])
    print(result["final_answer"])


if __name__ == "__main__":
    main()
