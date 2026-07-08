"""分阶段级联模式 —— 生产里最常见的形态。

Stage 1: 意图分类（纯 Python，不浪费 LLM）
  → 分支路由（搜索 / 报价 / 问答 / 闲聊）
Stage 2: 工具执行（每个分支独立处理，真实场景可挂 LLM+Tool 子图）
Stage 3: 格式化输出（纯 Python）

关键价值：只在真正需要 LLM 思考的地方用 LLM，整体成本和延迟比纯 ReAct 低一个数量级。

需要依赖：pip install langgraph langchain-openai
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示分阶段级联，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    query: str
    intent: str
    raw: str
    output: str


# ---------- Stage 1: 意图分类（纯 Python） ----------
def classify(state: State) -> dict:
    q = state["query"]
    if "查" in q:
        return {"intent": "search"}
    if "报价" in q or "多少钱" in q:
        return {"intent": "quote"}
    if "?" in q or "？" in q or "怎么" in q:
        return {"intent": "qa"}
    return {"intent": "chitchat"}


# ---------- Stage 2: 工具执行（各分支独立） ----------
def do_search(state: State) -> dict:
    return {"raw": "查询到 3 条记录"}


def do_quote(state: State) -> dict:
    return {"raw": "报价 ¥9999"}


def do_qa(state: State) -> dict:
    return {"raw": "根据知识库：..."}


def do_chitchat(state: State) -> dict:
    return {"raw": "你好呀～"}


# ---------- Stage 3: 格式化输出（纯 Python） ----------
def format_output(state: State) -> dict:
    return {"output": f"【{state['intent']}】{state['raw']}"}


def build_app():
    graph = StateGraph(State)
    graph.add_node("classify", classify)
    graph.add_node("search", do_search)
    graph.add_node("quote", do_quote)
    graph.add_node("qa", do_qa)
    graph.add_node("chitchat", do_chitchat)
    graph.add_node("format", format_output)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        lambda s: s["intent"],
        {"search": "search", "quote": "quote", "qa": "qa", "chitchat": "chitchat"},
    )
    for branch in ("search", "quote", "qa", "chitchat"):
        graph.add_edge(branch, "format")  # 分支汇合到 Stage 3
    graph.add_edge("format", END)
    return graph.compile()


def main() -> None:
    app = build_app()
    for q in ["帮我查订单", "这台多少钱", "这个怎么用？", "在吗"]:
        print(f"{q!r:14} → {app.invoke({'query': q})['output']}")


if __name__ == "__main__":
    main()
