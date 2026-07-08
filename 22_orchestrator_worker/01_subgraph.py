"""Subgraph 完整封装示例 —— 把编译好的子图当主图的一个节点。

主图执行到子图节点时，把当前 State 传给子图，子图跑完把更新后的 State 返回主图。
三个工程红利：可独立测试、可复用、State 隔离。

需要依赖：pip install langgraph
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph")
    print("（本示例演示 Subgraph 封装，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    text: str
    chunks: list
    vectors: list
    result: str


# ---------- 子图：语义切块 + 向量化（可被任意 RAG 项目复用） ----------
def node_a(state: State) -> dict:
    return {"chunks": state["text"].split("。")}


def node_b(state: State) -> dict:
    return {"vectors": [f"vec({c})" for c in state["chunks"] if c]}


def build_subgraph():
    sub_graph = StateGraph(State)
    sub_graph.add_node("a", node_a)
    sub_graph.add_node("b", node_b)
    sub_graph.add_edge(START, "a")
    sub_graph.add_edge("a", "b")
    sub_graph.add_edge("b", END)
    return sub_graph.compile()


# ---------- 主图：把子图当节点用 ----------
def preprocess(state: State) -> dict:
    return {"text": state["text"].strip()}


def postprocess(state: State) -> dict:
    return {"result": f"生成 {len(state['vectors'])} 个向量"}


def build_main():
    compiled_sub = build_subgraph()
    main_graph = StateGraph(State)
    main_graph.add_node("preprocess", preprocess)
    main_graph.add_node("sub_flow", compiled_sub)  # ← 关键！子图作为节点
    main_graph.add_node("postprocess", postprocess)
    main_graph.add_edge(START, "preprocess")
    main_graph.add_edge("preprocess", "sub_flow")
    main_graph.add_edge("sub_flow", "postprocess")
    main_graph.add_edge("postprocess", END)
    return main_graph.compile()


def main() -> None:
    # 红利①：子图可独立测试
    sub = build_subgraph()
    print("子图独立测试：", sub.invoke({"text": "句子一。句子二。句子三"}))

    # 主图里复用同一子图
    app = build_main()
    result = app.invoke({"text": "  LangGraph 很好用。子图可以复用  "})
    print("主图执行：", result["result"])


if __name__ == "__main__":
    main()
