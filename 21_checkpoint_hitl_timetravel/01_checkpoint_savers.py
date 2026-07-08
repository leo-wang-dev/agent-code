"""Checkpoint 三种 saver 对照 —— MemorySaver / SqliteSaver / PostgresSaver。

| Checkpointer | 适用            | 部署成本      |
|--------------|-----------------|---------------|
| MemorySaver  | 单元测试 / Demo | 零            |
| SqliteSaver  | 单机生产/小流量 | 低（一个文件）|
| PostgresSaver| 多实例/高并发   | 中（需要 PG） |

本文件用 MemorySaver 实跑一遍"会话持久化 + 凭 thread_id 恢复"，
并探测 Sqlite / Postgres saver 是否可用（可选依赖）。

需要依赖：pip install langgraph
可选：pip install langgraph-checkpoint-sqlite langgraph-checkpoint-postgres
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    print("需要先安装依赖：pip install langgraph")
    print("（本示例演示三种 checkpointer，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    query: str
    history: Annotated[list, operator.add]
    turn: int


def respond(state: State) -> dict:
    turn = state.get("turn", 0) + 1
    return {"history": [f"第 {turn} 轮：{state['query']}"], "turn": turn}


def build_app(checkpointer):
    graph = StateGraph(State)
    graph.add_node("respond", respond)
    graph.add_edge(START, "respond")
    graph.add_edge("respond", END)
    return graph.compile(checkpointer=checkpointer)


def probe_optional_savers() -> None:
    print("\n三种 saver 可用性：")
    print("  MemorySaver   : 可用（langgraph 内置）")
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: F401
        print("  SqliteSaver   : 可用（已安装 langgraph-checkpoint-sqlite）")
    except ImportError:
        print("  SqliteSaver   : 未安装 → pip install langgraph-checkpoint-sqlite")
    try:
        from langgraph.checkpoint.postgres import PostgresSaver  # noqa: F401
        print("  PostgresSaver : 可用（已安装 langgraph-checkpoint-postgres，还需 PG 实例）")
    except ImportError:
        print("  PostgresSaver : 未安装 → pip install langgraph-checkpoint-postgres")


def main() -> None:
    # 用 MemorySaver 演示持久化：同一 thread_id 多次调用会累积历史
    app = build_app(MemorySaver())
    config = {"configurable": {"thread_id": "user_123_session_456"}}

    app.invoke({"query": "第一个问题"}, config=config)
    app.invoke({"query": "继续上次的问题"}, config=config)  # 自动从上次 state 继续

    state = app.get_state(config)
    print("凭 thread_id 恢复出的完整历史：")
    for line in state.values["history"]:
        print("  -", line)
    print(f"累计轮次 turn={state.values['turn']}")

    probe_optional_savers()
    print("\n提示：生产永远不要用 MemorySaver（重启即丢）；单机用 Sqlite，多实例用 Postgres。")


if __name__ == "__main__":
    main()
