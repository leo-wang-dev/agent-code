"""Annotated Reducer 对照实验 —— 有 reducer vs 没有 reducer。

想象一个采购助手，多个节点都可能调工具，你想把所有工具调用记录起来审计。
  - 没有 reducer：每个节点都要 .copy() + .append()，模板代码到处都是、易出错
  - 有  reducer：节点只关心自己产生了什么，框架负责合并

有 langgraph 时用真实图跑；没有则用 stdlib 模拟合并语义，两种情况都可运行。
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

HAS_LANGGRAPH = True
try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    HAS_LANGGRAPH = False


# ---------- 没有 reducer 的做法：节点自己维护列表 ----------
def without_reducer() -> list:
    state: dict = {"tool_trace": []}

    def search_node(state):
        trace = state.get("tool_trace", []).copy()
        trace.append("called search")
        return {"tool_trace": trace}

    def quote_node(state):
        trace = state.get("tool_trace", []).copy()
        trace.append("called quote")
        return {"tool_trace": trace}

    # 手工把节点串起来（覆盖式合并）
    state.update(search_node(state))
    state.update(quote_node(state))
    return state["tool_trace"]


# ---------- 有 reducer 的做法：节点只返回新增项 ----------
class State(TypedDict):
    tool_trace: Annotated[list, operator.add]  # 自动累加


def search_node(state: State) -> dict:
    return {"tool_trace": ["called search"]}  # 直接返回新增项


def quote_node(state: State) -> dict:
    return {"tool_trace": ["called quote"]}   # 框架自动追加


def with_reducer_langgraph() -> list:
    graph = StateGraph(State)
    graph.add_node("search", search_node)
    graph.add_node("quote", quote_node)
    graph.add_edge(START, "search")
    graph.add_edge("search", "quote")
    graph.add_edge("quote", END)
    app = graph.compile()
    return app.invoke({"tool_trace": []})["tool_trace"]


def with_reducer_simulated() -> list:
    # 无 langgraph 时，用 operator.add 模拟框架的字段级合并
    trace: list = []
    trace = operator.add(trace, search_node({"tool_trace": trace})["tool_trace"])
    trace = operator.add(trace, quote_node({"tool_trace": trace})["tool_trace"])
    return trace


def main() -> None:
    print("没有 reducer（节点手动 copy+append）:", without_reducer())
    if HAS_LANGGRAPH:
        print("有 reducer（LangGraph 真实图自动合并）:", with_reducer_langgraph())
    else:
        print("（未安装 langgraph，改用 stdlib 模拟框架合并语义）")
        print("有 reducer（模拟框架自动合并）      :", with_reducer_simulated())
        print("安装 langgraph 后可跑真实图：pip install langgraph langchain-openai")


if __name__ == "__main__":
    main()
