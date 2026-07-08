"""Plan-and-Execute 完整实现 —— Planner / Executor / Replanner 三节点结构。

适合"步骤明确、流程可枚举"的任务（数据分析、报告生成、固定流程自动化）。
  Planner   ← 把任务拆成步骤列表
  Executor  ← 按列表依次执行每一步（每步内部可以是 ReAct 子 Agent）
  Replanner ← 看执行结果，决定是否调整剩余计划 / 是否收尾

本文件用 mock 函数替代 LLM 规划，无需密钥即可跑通完整状态机。

需要依赖：pip install langgraph langchain-openai
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示 Plan-and-Execute，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class PlanExecuteState(TypedDict, total=False):
    input: str
    plan: list[str]          # 当前的步骤计划
    past_steps: list[tuple]  # 已执行的步骤 + 结果
    response: str            # 最终答案


# ---------- 以下三个函数在真实场景由 LLM 完成，这里用 mock ----------
def call_llm_for_plan(prompt: str) -> list[str]:
    return ["收集销售数据", "计算同比环比", "生成图表", "撰写结论"]


def execute_step(step: str) -> str:
    return f"「{step}」已完成"


def synthesize_answer(past_steps: list[tuple]) -> str:
    done = "；".join(s for s, _ in past_steps)
    return f"报告已生成，覆盖步骤：{done}"


def adjust_plan(state: PlanExecuteState) -> list[str]:
    return state["plan"]  # mock：不调整


def planner(state: PlanExecuteState) -> dict:
    prompt = f"将以下任务拆成 3-5 个可执行步骤：{state['input']}"
    return {"plan": call_llm_for_plan(prompt)}


def executor(state: PlanExecuteState) -> dict:
    current_step = state["plan"][0]
    result = execute_step(current_step)  # 内部可以是个 ReAct 子 Agent
    return {
        "past_steps": state.get("past_steps", []) + [(current_step, result)],
        "plan": state["plan"][1:],  # 移除已执行的步骤
    }


def replanner(state: PlanExecuteState) -> dict:
    if not state["plan"]:
        return {"response": synthesize_answer(state["past_steps"])}
    return {"plan": adjust_plan(state)}


def should_end(state: PlanExecuteState) -> str:
    return "end" if state.get("response") else "executor"


def build_app():
    graph = StateGraph(PlanExecuteState)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("replanner", replanner)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "replanner")
    graph.add_conditional_edges("replanner", should_end, {"end": END, "executor": "executor"})
    return graph.compile()


def main() -> None:
    app = build_app()
    result = app.invoke({"input": "生成上季度销售分析报告", "past_steps": []})
    print("执行轨迹：")
    for step, res in result["past_steps"]:
        print(f"  - {step} → {res}")
    print("最终答案：", result["response"])


if __name__ == "__main__":
    main()
