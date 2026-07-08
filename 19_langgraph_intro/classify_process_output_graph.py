"""完整的"分类 → 处理 → 输出"小图。

把 5 个概念拼成第一个可跑的状态机 Agent：
  分类(classify) → 条件路由到处理节点(weather/general) → 统一输出(output)

整个流程没有一个 while 循环——状态机自己跑；路由是纯 Python 函数（不调 LLM）。

需要 langgraph：pip install langgraph langchain-openai
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示完整分类-处理-输出小图，缺少 langgraph 无法运行）")
    raise SystemExit(0)


# Step 1: 定义 State
class State(TypedDict, total=False):
    query: str
    intent: str
    answer: str
    output: str


# Step 2: 定义 Nodes —— 分类 / 处理 / 输出
def classify(state: State) -> dict:
    if "天气" in state["query"]:
        return {"intent": "weather"}
    return {"intent": "general"}


def handle_weather(state: State) -> dict:
    return {"answer": "今天天气晴朗"}


def handle_general(state: State) -> dict:
    return {"answer": "我帮你查询..."}


def output(state: State) -> dict:
    return {"output": f"[{state['intent']}] {state['answer']}"}


def build_app():
    # Step 3: 建图
    graph = StateGraph(State)
    graph.add_node("classify", classify)
    graph.add_node("weather", handle_weather)
    graph.add_node("general", handle_general)
    graph.add_node("output", output)

    # Step 4: 连边
    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        lambda s: s["intent"],
        {"weather": "weather", "general": "general"},
    )
    graph.add_edge("weather", "output")
    graph.add_edge("general", "output")
    graph.add_edge("output", END)

    # Step 5: 编译
    return graph.compile()


def main() -> None:
    app = build_app()
    for query in ["今天天气怎么样", "帮我查一下订单"]:
        result = app.invoke({"query": query})
        print(result["output"])


if __name__ == "__main__":
    main()
