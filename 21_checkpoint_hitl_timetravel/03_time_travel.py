"""Time Travel 历史回放 demo —— 流程的 "git checkout"。

Checkpoint 会保留所有历史快照，可以拉出任意历史 checkpoint 从那一步重新执行。
用途：线上 bug 复现 / 从问题节点重跑 / A-B 测试 / 流程改写后回归测试。

API：
  app.get_state_history(config)  # 列出所有 checkpoint
  app.invoke(None, config={..., "checkpoint_id": cp_id})  # 从指定快照继续

需要依赖：pip install langgraph
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    print("需要先安装依赖：pip install langgraph")
    print("（本示例演示 Time Travel 历史回放，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    query: str
    intent: str
    results: list
    top_3: list
    answer: str


def classify(state: State) -> dict:
    return {"intent": "search"}


def search(state: State) -> dict:
    return {"results": ["doc1", "doc2", "doc3", "doc4"]}


def rerank(state: State) -> dict:
    return {"top_3": state["results"][:3]}


def generate(state: State) -> dict:
    return {"answer": f"基于 {state['top_3']} 的答案"}


def build_app():
    graph = StateGraph(State)
    for name, fn in [("classify", classify), ("search", search), ("rerank", rerank), ("generate", generate)]:
        graph.add_node(name, fn)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "search")
    graph.add_edge("search", "rerank")
    graph.add_edge("rerank", "generate")
    graph.add_edge("generate", END)
    return graph.compile(checkpointer=MemorySaver())


def main() -> None:
    app = build_app()
    config = {"configurable": {"thread_id": "abc"}}
    app.invoke({"query": "查一下资料"}, config=config)

    # 列出某个会话的所有 checkpoint（get_state_history 返回从新到旧）
    history = list(app.get_state_history(config))
    print("完整 checkpoint 链（从旧到新）：")
    search_done_cp = None
    for cp in reversed(history):
        step = cp.metadata.get("step")
        print(f"  step={step}  next={cp.next}  values_keys={list(cp.values.keys())}")
        # 记下 search 完成后的快照（此后 next 指向 rerank）
        if cp.next == ("rerank",):
            search_done_cp = cp

    # 从 search 完成后的 checkpoint 重新执行（比如修好了 rerank 的 bug，无需用户重问）
    if search_done_cp is not None:
        print("\n从 search 完成后的快照 Time Travel 重跑：")
        result = app.invoke(None, config=search_done_cp.config)
        print("  重跑得到答案：", result["answer"])


if __name__ == "__main__":
    main()
