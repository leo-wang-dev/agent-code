"""Agent / Task / Crew 三件套示例。

CrewAI 的核心心智：Agent 是"角色"（role/goal/backstory 会注入 system prompt），
Task 是一等公民的工作单元（expected_output 是契约、agent 显式绑定执行者、
context 显式声明依赖），Crew 把 Agent 和 Task 打包并 kickoff。

无 OPENAI_API_KEY 时：仍能构造全部对象（演示真实 API），只是不发起真实 kickoff。

需要依赖：pip install crewai
"""
from __future__ import annotations

import os

# 占位 key 让对象可构造；关闭 CrewAI 首次运行的 tracing/telemetry 交互提示
os.environ.setdefault("OPENAI_API_KEY", "sk-demo-placeholder")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

HAS_REAL_KEY = os.environ["OPENAI_API_KEY"] != "sk-demo-placeholder"

try:
    from crewai import Agent, Task, Crew, Process
except ImportError:
    print("需要先安装依赖：pip install crewai")
    print("（本示例演示 Agent/Task/Crew 三件套，缺少 crewai 无法运行）")
    raise SystemExit(0)


def build_crew() -> "Crew":
    researcher = Agent(
        role="资深市场研究员",
        goal="找到某个产品在中国市场的最新趋势和数据",
        backstory=(
            "你是一位有 10 年经验的市场研究员，擅长从公开数据中找出有价值的洞察。"
            "你做事严谨，不喜欢用未经验证的信息支撑结论。"
        ),
        verbose=False,
    )
    writer = Agent(
        role="市场分析文章作者",
        goal="把研究结论写成清晰有据的中文分析文章",
        backstory="你擅长把枯燥的数据变成读者爱看的分析文章。",
        verbose=False,
    )

    research_task = Task(
        description="研究 2025 年中国新能源汽车市场的销量数据，找出 Top 5 品牌和它们的增长率",
        expected_output="一份结构化报告：1) Top 5 品牌 2) 每个品牌销量 3) 同比增长率",
        agent=researcher,  # 显式绑定执行者
    )
    writing_task = Task(
        description="基于研究报告写一篇 1500 字的市场分析文章",
        expected_output="一篇结构清晰、有数据支撑的中文分析文章",
        agent=writer,
        context=[research_task],  # 显式声明依赖：自动拿到 research 的输出
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
        verbose=False,
    )


def main() -> None:
    crew = build_crew()
    print("Crew 构造成功：")
    print("  Agents:", [a.role for a in crew.agents])
    print("  Tasks :", [t.description[:16] + "…" for t in crew.tasks])
    print("  Process:", crew.process)

    if HAS_REAL_KEY:
        print("\n检测到真实 OPENAI_API_KEY，执行 crew.kickoff()：")
        result = crew.kickoff()
        print(result)
    else:
        print("\n未检测到真实 OPENAI_API_KEY，跳过 kickoff()。")
        print("设置 OPENAI_API_KEY 后运行即可看到研究员→作者的真实流水线输出。")


if __name__ == "__main__":
    main()
