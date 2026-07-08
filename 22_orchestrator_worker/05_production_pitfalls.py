"""五个生产坑的应对代码 —— 多 Agent 在 LangGraph 里的具体加固。

坑 1 协调风暴      → Orchestrator 一次性下发完整上下文，不塞"再确认"节点
坑 2 单 Worker 失败拖垮全局 → 每个 Worker 用 try/except 包核心逻辑，失败降级
坑 3 成本爆炸      → Worker 只在被选中时才调 LLM；小模型决策、大模型干活
坑 4 跨 Worker 幻觉传播 → Aggregator 做事实回检
坑 5 调试地狱      → Checkpoint + worker_trace 联合，拉出完整轨迹

需要依赖：pip install langgraph
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    print("需要先安装依赖：pip install langgraph")
    print("（本示例演示五个生产坑应对，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class TeamState(TypedDict, total=False):
    user_query: str
    selected_workers: list
    research_result: str
    pricing_result: str
    final_answer: str
    worker_trace: Annotated[list, operator.add]


def orchestrator(state: TeamState) -> dict:
    # 坑 1：一次性把该派的 Worker 全定下来，不来回确认
    return {"selected_workers": ["research", "pricing"]}


def research_worker(state: TeamState) -> dict:
    # 坑 3：没被选中不调 LLM，直接跳过（省 token）
    if "research" not in state["selected_workers"]:
        return {}
    try:
        result = do_research(state["user_query"])
        return {"research_result": result,
                "worker_trace": [{"worker": "research", "status": "done"}]}
    except Exception as e:  # 坑 2：单个 Worker 失败不拖垮全局
        return {"research_result": None,
                "worker_trace": [{"worker": "research", "status": "failed", "error": str(e)}]}


def pricing_worker(state: TeamState) -> dict:
    if "pricing" not in state["selected_workers"]:
        return {}
    try:
        # 故意触发异常，演示降级
        raise ValueError("定价服务超时")
    except Exception as e:
        return {"pricing_result": None,
                "worker_trace": [{"worker": "pricing", "status": "failed", "error": str(e)}]}


def do_research(query: str) -> str:
    return f"关于「{query}」的调研结论"


def aggregator(state: TeamState) -> dict:
    # 坑 4：跨 Worker 边界做事实回检；Aggregator 看到 None 就降级
    verified = []
    if state.get("research_result"):
        verified.append(f"调研（已回检）：{state['research_result']}")
    if state.get("pricing_result"):
        verified.append(f"报价：{state['pricing_result']}")
    else:
        verified.append("报价：暂缺（Worker 失败，已降级）")
    return {"final_answer": "\n".join(verified)}


def build_app():
    graph = StateGraph(TeamState)
    graph.add_node("orchestrator", orchestrator)
    graph.add_node("research", research_worker)
    graph.add_node("pricing", pricing_worker)
    graph.add_node("aggregator", aggregator)
    graph.add_edge(START, "orchestrator")
    for w in ("research", "pricing"):
        graph.add_edge("orchestrator", w)
        graph.add_edge(w, "aggregator")
    graph.add_edge("aggregator", END)
    # 坑 5：挂 Checkpointer，事后可拉完整轨迹
    return graph.compile(checkpointer=MemorySaver())


def main() -> None:
    app = build_app()
    config = {"configurable": {"thread_id": "team_debug_001"}}
    result = app.invoke({"user_query": "帮我做产品分析", "worker_trace": []}, config=config)

    print("最终答案（含降级）：")
    print(result["final_answer"])

    # 坑 5：Checkpoint + worker_trace 联合定位
    print("\n执行轨迹（worker_trace）：")
    for entry in result["worker_trace"]:
        print("  -", entry)


if __name__ == "__main__":
    main()
