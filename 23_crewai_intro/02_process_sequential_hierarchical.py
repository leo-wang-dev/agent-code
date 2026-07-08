"""Sequential vs Hierarchical 两种 Process 对照。

Sequential —— 流水线模式：任务按代码顺序执行，前一个 Task 输出自动成为下一个的上下文。
Hierarchical —— 经理模式：框架自动生成 Manager Agent，动态决定分配/顺序/是否重做。

生产经验：80% 场景用 Sequential（可预测、可调试、可解释）；
Hierarchical 的 Manager 决策本身是个 LLM 调用，存在不稳定性。

无 OPENAI_API_KEY 时仅构造并对照两种 Crew，不发起真实 kickoff。

需要依赖：pip install crewai
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-demo-placeholder")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

HAS_REAL_KEY = os.environ["OPENAI_API_KEY"] != "sk-demo-placeholder"

try:
    from crewai import Agent, Task, Crew, Process
except ImportError:
    print("需要先安装依赖：pip install crewai")
    print("（本示例演示 Sequential/Hierarchical，缺少 crewai 无法运行）")
    raise SystemExit(0)


def make_agents():
    researcher = Agent(role="研究员", goal="调研数据", backstory="资深研究员", verbose=False)
    writer = Agent(role="写手", goal="写文章", backstory="资深撰稿人", verbose=False)
    editor = Agent(role="编辑", goal="润色定稿", backstory="严格的主编", verbose=False)
    return researcher, writer, editor


def build_sequential() -> "Crew":
    researcher, writer, editor = make_agents()
    research_task = Task(description="调研市场", expected_output="报告", agent=researcher)
    writing_task = Task(description="写文章", expected_output="文章", agent=writer)
    editing_task = Task(description="润色", expected_output="终稿", agent=editor)
    return Crew(
        agents=[researcher, writer, editor],
        tasks=[research_task, writing_task, editing_task],
        process=Process.sequential,  # 顺序：research → writing → editing
        verbose=False,
    )


def build_hierarchical() -> "Crew":
    researcher, writer, editor = make_agents()
    # 只给一个高层任务，Manager 自己决定怎么拆
    user_request_task = Task(
        description="就新能源汽车市场产出一篇可发布的分析文章",
        expected_output="一篇经过校对的分析文章",
        agent=researcher,
    )
    return Crew(
        agents=[researcher, writer, editor],
        tasks=[user_request_task],
        process=Process.hierarchical,
        manager_llm="gpt-4o",  # Manager 用什么模型
        verbose=False,
    )


def main() -> None:
    seq = build_sequential()
    hier = build_hierarchical()

    print("Sequential（流水线）：", len(seq.tasks), "个任务按顺序执行 →",
          [a.role for a in seq.agents])
    print("Hierarchical（经理）：", len(hier.tasks), "个高层任务，Manager 动态分工；",
          "manager_llm =", hier.manager_llm)

    print("\n选型：流程明确用 Sequential；组合不确定/需动态分工用 Hierarchical；")
    print("     需要高度精确路由控制则改用 LangGraph。")

    if HAS_REAL_KEY:
        print("\n检测到真实 key，执行 Sequential kickoff：")
        print(seq.kickoff())
    else:
        print("\n未检测到真实 OPENAI_API_KEY，跳过 kickoff()（仅对照结构）。")


if __name__ == "__main__":
    main()
