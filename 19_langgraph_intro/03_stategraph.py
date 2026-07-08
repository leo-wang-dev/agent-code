"""概念 3：StateGraph —— 图容器。

把 Node 和 Edge 装进 StateGraph。StateGraph 本身没有魔法，
就是个"节点 + 边"的容器。真正的能力来自 Edge（概念 4）。

需要 langgraph：pip install langgraph langchain-openai
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示 StateGraph 图容器，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class AgentState(TypedDict, total=False):
    user_query: str
    intent: str
    answer: str


def classify_intent(state: AgentState) -> dict:
    return {"intent": "search" if "查询" in state["user_query"] else "chitchat"}


def do_search(state: AgentState) -> dict:
    return {"answer": "已为你查询到结果"}


def do_quote(state: AgentState) -> dict:
    return {"answer": "报价：¥9999"}


def handle_chitchat(state: AgentState) -> dict:
    return {"answer": "你好呀～"}


def main() -> None:
    graph = StateGraph(AgentState)
    graph.add_node("classify", classify_intent)
    graph.add_node("search", do_search)
    graph.add_node("quote", do_quote)
    graph.add_node("chitchat", handle_chitchat)

    print("已装入 StateGraph 的节点：")
    for name in ("classify", "search", "quote", "chitchat"):
        print("  -", name)
    print("\n注意：此时还没有连边，图不可运行。边（Edge）见概念 4。")


if __name__ == "__main__":
    main()
