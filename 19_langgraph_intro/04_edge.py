"""概念 4：Edge —— 控制流。

两种边：
  ① add_edge —— 确定性顺序（A 完了一定执行 B）
  ② add_conditional_edges —— 条件分支（路由函数返回节点名，框架直接跳转）

核心哲学：路由是代码决定的，不是 LLM 决定的。路由不再是概率事件。

需要 langgraph：pip install langgraph langchain-openai
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示 Edge 控制流，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class AgentState(TypedDict, total=False):
    user_query: str
    intent: str
    answer: str


def classify(state: AgentState) -> dict:
    if "查询" in state["user_query"]:
        return {"intent": "search"}
    elif "报价" in state["user_query"]:
        return {"intent": "quote"}
    return {"intent": "chitchat"}


def do_search(state: AgentState) -> dict:
    return {"answer": "已查询到结果"}


def do_quote(state: AgentState) -> dict:
    return {"answer": "报价：¥9999"}


def handle_chitchat(state: AgentState) -> dict:
    return {"answer": "你好呀～"}


def route(state: AgentState) -> str:
    return state["intent"]  # 返回的字符串就是下一个节点名


def build_app():
    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("search", do_search)
    graph.add_node("quote", do_quote)
    graph.add_node("chitchat", handle_chitchat)

    graph.add_edge(START, "classify")
    # 条件分支：路由函数返回节点名
    graph.add_conditional_edges(
        "classify",
        route,
        {"search": "search", "quote": "quote", "chitchat": "chitchat"},
    )
    # 确定性顺序：三个处理节点都直接到 END
    graph.add_edge("search", END)
    graph.add_edge("quote", END)
    graph.add_edge("chitchat", END)
    return graph.compile()


def main() -> None:
    app = build_app()
    for query in ["帮我查询订单", "给我报价", "在吗"]:
        result = app.invoke({"user_query": query})
        print(f"{query!r:16} → intent={result['intent']:9} answer={result['answer']}")


if __name__ == "__main__":
    main()
