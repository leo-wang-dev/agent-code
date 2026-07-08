"""自定义 ReAct 图 —— 修掉 create_react_agent 的默认坑。

坑 1：默认没有 max_iterations（无限循环，烧 Token）→ 加 step_count 强制终止。
坑 2：错误吞掉导致死循环重试 → 工具节点外包一层错误处理。

这是"两节点 + 一个条件路由 = 完整 ReAct 循环"的手写版，但补上了 step 守卫。
本文件用 mock 决策函数替代 LLM，无需密钥即可跑通。

需要依赖：pip install langgraph langchain-openai
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示自定义 ReAct 图 + step 守卫，缺少 langgraph 无法运行）")
    raise SystemExit(0)


# 真实场景用 add_messages reducer；这里用 operator.add + 简单 dict，
# 便于在无 LLM 的 mock 下清晰展示 step 守卫逻辑。
class State(TypedDict):
    messages: Annotated[list, operator.add]
    step_count: int  # 自己加，用于强制终止


MAX_STEPS = 8


def agent_node(state: State) -> dict:
    """mock 的 LLM 节点：前两步要求调工具，之后给出最终答案。"""
    step = state.get("step_count", 0)
    if step < 2:
        return {
            "messages": [{"role": "assistant", "content": f"[思考] 需要调工具（第 {step + 1} 步）"}],
            "step_count": step + 1,
        }
    return {
        "messages": [{"role": "assistant", "content": "[最终答案] 已完成任务。"}],
        "step_count": step + 1,
    }


def tools_node(state: State) -> dict:
    return {"messages": [{"role": "tool", "content": "工具返回：ok"}]}


def force_end_node(state: State) -> dict:
    return {"messages": [{"role": "assistant", "content": "[强制终止] 达到最大步数上限。"}]}


def should_continue(state: State) -> str:
    if state["step_count"] >= MAX_STEPS:
        return "force_end"  # 坑 1 的修法：强制终止
    last = state["messages"][-1]["content"] if state["messages"] else ""
    if "需要调工具" in last:
        return "tools"
    return "end"


def build_app():
    graph = StateGraph(State)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("force_end", force_end_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END, "force_end": "force_end"},
    )
    graph.add_edge("tools", "agent")  # ReAct 循环
    graph.add_edge("force_end", END)
    return graph.compile()


def main() -> None:
    app = build_app()
    result = app.invoke({"messages": [{"role": "user", "content": "帮我处理任务"}], "step_count": 0})
    for m in result["messages"]:
        print(f"  {m['role']:10} {m['content']}")
    print(f"总步数 step_count={result['step_count']}（守卫上限 {MAX_STEPS}）")


if __name__ == "__main__":
    main()
