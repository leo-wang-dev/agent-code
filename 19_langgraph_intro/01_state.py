"""概念 1：State —— 全局状态容器。

LangGraph 的状态用 Python 的 TypedDict 定义，两个关键设计点：
  ① TypedDict = 静态契约（强类型，所有节点共享同一份定义）
  ② Annotated Reducer = 字段级聚合（新值不是覆盖，而是按 reducer 合并）

本文件纯 stdlib，可直接运行，演示 reducer 的合并语义。
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict, get_type_hints


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]  # 自动累加
    user_query: str                          # 单个值，会被覆盖
    intent: str
    search_results: list
    final_answer: str


def merge(state: dict, update: dict, hints: dict) -> dict:
    """手工模拟 LangGraph 框架对节点返回值的合并逻辑。

    有 reducer（Annotated）的字段用 reducer 合并；否则直接覆盖。
    """
    result = dict(state)
    for key, value in update.items():
        annotation = hints.get(key)
        reducer = getattr(annotation, "__metadata__", (None,))[0]
        if reducer is not None:  # 有 reducer → 合并
            result[key] = reducer(result.get(key, []), value)
        else:                    # 无 reducer → 覆盖
            result[key] = value
    return result


def main() -> None:
    hints = get_type_hints(AgentState, include_extras=True)

    state: dict = {"messages": [], "user_query": "帮我查一下张三的信息"}
    print("初始 state:", state)

    # 节点 A 返回：{"messages": ["hello"]}
    state = merge(state, {"messages": ["hello"]}, hints)
    # 节点 B 返回：{"messages": ["world"]}
    state = merge(state, {"messages": ["world"]}, hints)
    print("messages 有 reducer → 自动追加:", state["messages"])

    # intent 无 reducer → 覆盖
    state = merge(state, {"intent": "search"}, hints)
    state = merge(state, {"intent": "quote"}, hints)
    print("intent 无 reducer → 覆盖为:", state["intent"])


if __name__ == "__main__":
    main()
