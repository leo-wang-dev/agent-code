"""条件循环示例 —— 让任意节点带循环（不只是工具调用循环）。

              ┌────────────┐
              ↓            │
[draft] → [review] → [revise]──┘   ← 修改不通过就回到 review
              │
            通过
              ↓
            END

实现：add_conditional_edges("review", check_approval, {"pass": END, "revise": "revise"})

需要依赖：pip install langgraph langchain-openai
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示条件循环，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    content: str
    quality: int      # 0-100，评审打分
    revisions: int    # 已修改次数


PASS_SCORE = 80
MAX_REVISIONS = 5


def draft(state: State) -> dict:
    return {"content": "初稿内容", "quality": 50, "revisions": 0}


def review(state: State) -> dict:
    # mock 评审：每次修改后质量提升
    score = min(100, 50 + state.get("revisions", 0) * 20)
    return {"quality": score}


def revise(state: State) -> dict:
    n = state.get("revisions", 0) + 1
    return {"content": f"第 {n} 次修订稿", "revisions": n}


def check_approval(state: State) -> str:
    if state["quality"] >= PASS_SCORE or state.get("revisions", 0) >= MAX_REVISIONS:
        return "pass"
    return "revise"


def build_app():
    graph = StateGraph(State)
    graph.add_node("draft", draft)
    graph.add_node("review", review)
    graph.add_node("revise", revise)

    graph.add_edge(START, "draft")
    graph.add_edge("draft", "review")
    graph.add_conditional_edges("review", check_approval, {"pass": END, "revise": "revise"})
    graph.add_edge("revise", "review")  # 循环回评审
    return graph.compile()


def main() -> None:
    app = build_app()
    result = app.invoke({})
    print(f"最终稿：{result['content']}")
    print(f"质量分：{result['quality']}  修订次数：{result['revisions']}")


if __name__ == "__main__":
    main()
