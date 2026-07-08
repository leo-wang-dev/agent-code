"""并行 fan-out / fan-in 示例 —— 并行执行多个独立任务后汇总。

              ┌→ [search_api_1]
[task_split] ─┼→ [search_api_2] ─→ [merge_results]
              └→ [search_api_3]

LangGraph 原生支持并行节点：只要让它们都连到同一个下游节点，
框架就会等所有并行节点完成再 fan-in。并行分支写入的字段需要用 reducer 合并。

需要依赖：pip install langgraph langchain-openai
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示 fan-out/fan-in 并行，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    query: str
    results: Annotated[list, operator.add]  # 并行分支各写一条，reducer 自动合并
    merged: str


def task_split(state: State) -> dict:
    return {}  # 仅作为 fan-out 起点


def search_api_1(state: State) -> dict:
    return {"results": [f"API1: {state['query']} 命中 5 条"]}


def search_api_2(state: State) -> dict:
    return {"results": [f"API2: {state['query']} 命中 3 条"]}


def search_api_3(state: State) -> dict:
    return {"results": [f"API3: {state['query']} 命中 8 条"]}


def merge_results(state: State) -> dict:
    return {"merged": " | ".join(sorted(state["results"]))}


def build_app():
    graph = StateGraph(State)
    graph.add_node("task_split", task_split)
    graph.add_node("search_api_1", search_api_1)
    graph.add_node("search_api_2", search_api_2)
    graph.add_node("search_api_3", search_api_3)
    graph.add_node("merge_results", merge_results)

    graph.add_edge(START, "task_split")
    # fan-out：一个节点连到多个并行节点
    for api in ("search_api_1", "search_api_2", "search_api_3"):
        graph.add_edge("task_split", api)
        # fan-in：都连到同一下游，框架等全部完成
        graph.add_edge(api, "merge_results")
    graph.add_edge("merge_results", END)
    return graph.compile()


def main() -> None:
    app = build_app()
    result = app.invoke({"query": "LangGraph", "results": []})
    print("并行收集结果：")
    for r in sorted(result["results"]):
        print("  -", r)
    print("合并：", result["merged"])


if __name__ == "__main__":
    main()
