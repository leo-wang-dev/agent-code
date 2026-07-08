"""条件路由 demo —— add_conditional_edges 的独立演示。

路由函数返回节点名，框架直接跳转。路由是纯 Python 函数（不调 LLM），
所以路由是代码确定性，不是概率事件。

需要 langgraph：pip install langgraph langchain-openai
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示条件路由，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    amount: float          # 订单金额
    tier: str              # 路由结果
    result: str


def assess(state: State) -> dict:
    amount = state["amount"]
    if amount >= 100000:
        return {"tier": "vip"}
    elif amount >= 10000:
        return {"tier": "normal"}
    return {"tier": "small"}


def vip_flow(state: State) -> dict:
    return {"result": "转专属客服 + 走加急审批"}


def normal_flow(state: State) -> dict:
    return {"result": "标准处理流程"}


def small_flow(state: State) -> dict:
    return {"result": "自动化处理，无需人工"}


def main() -> None:
    graph = StateGraph(State)
    graph.add_node("assess", assess)
    graph.add_node("vip", vip_flow)
    graph.add_node("normal", normal_flow)
    graph.add_node("small", small_flow)

    graph.add_edge(START, "assess")
    graph.add_conditional_edges(
        "assess",
        lambda s: s["tier"],  # 返回值即下一节点名
        {"vip": "vip", "normal": "normal", "small": "small"},
    )
    for node in ("vip", "normal", "small"):
        graph.add_edge(node, END)

    app = graph.compile()
    for amount in (500, 30000, 200000):
        out = app.invoke({"amount": amount})
        print(f"金额 {amount:>7} → tier={out['tier']:7} → {out['result']}")


if __name__ == "__main__":
    main()
