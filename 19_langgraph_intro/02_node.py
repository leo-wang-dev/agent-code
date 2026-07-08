"""概念 2：Node —— 普通 Python 函数。

一个 Node 就是普通函数：接收 state（整个状态），返回要更新的字段（部分 dict）。
关键点：Node 不一定包含 LLM。简单分类直接用 Python 写，
比让 LLM 判断快 100 倍、便宜 100 倍、稳定 100 倍。

本文件纯 stdlib，可直接运行。
"""
from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    user_query: str
    intent: str


def classify_intent(state: AgentState) -> dict:
    query = state["user_query"]
    if "查询" in query:
        return {"intent": "search"}
    elif "报价" in query:
        return {"intent": "quote"}
    return {"intent": "chitchat"}


def main() -> None:
    for query in ["帮我查询张三的订单", "给我报价一下这台机器", "在吗"]:
        update = classify_intent({"user_query": query})
        print(f"{query!r:20} → 节点返回 {update}")


if __name__ == "__main__":
    main()
