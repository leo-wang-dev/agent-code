"""概念 5：Compile —— 图变成可执行 app。

定义完图，要编译成 app 才能 invoke。编译这一步还能挂载重要工业级能力
（checkpointer 持久化、interrupt_before 人工审批），下一篇（21）会讲。

需要 langgraph：pip install langgraph langchain-openai
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示 compile 与 invoke，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    user_query: str
    final_answer: str


def answer(state: State) -> dict:
    return {"final_answer": f"针对「{state['user_query']}」的处理结果"}


def main() -> None:
    graph = StateGraph(State)
    graph.add_node("answer", answer)
    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)

    # 编译：图 → 可执行 app
    app = graph.compile()
    result = app.invoke({"user_query": "帮我查一下张三的信息"})
    print(result["final_answer"])

    # 编译时可挂载工业级能力（下一篇讲）：
    #   app = graph.compile(
    #       checkpointer=SqliteSaver(...),   # 持久化
    #       interrupt_before=["approval"],   # 人工审批节点
    #   )


if __name__ == "__main__":
    main()
