"""Memory 开启 demo —— CrewAI 一行开启内置 Memory。

crew = Crew(..., memory=True) 一行开启后自动获得三种 Memory：
  - Short-term：当前 Crew 运行内，任务间临时上下文
  - Long-term ：跨多次 kickoff()，SQLite 持久化
  - Entity    ：跨多次 kickoff()，识别并记住实体（人/公司/产品）

对比 Mem0：CrewAI Memory 是"Crew 自己的工作记忆"，Mem0 是"用户级长期记忆"，常叠加使用。
隐藏成本：默认用 OpenAI Embedding 做语义搜索，大量 kickoff 会偷偷涨费用——
生产可换本地 Embedding（bge-large-zh）或对不必要字段关 Memory。

无 OPENAI_API_KEY 时仅构造带 memory 的 Crew，不发起真实 kickoff。

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
    print("（本示例演示 Memory 开启，缺少 crewai 无法运行）")
    raise SystemExit(0)


def build_crew(memory: bool) -> "Crew":
    analyst = Agent(
        role="市场分析师",
        goal="分析市场并记住关键洞察，做增量更新",
        backstory="你会把上次分析的结论存进长期记忆，下次做增量更新而不是重头来。",
        verbose=False,
    )
    task = Task(
        description="分析新能源汽车市场，记录关键洞察",
        expected_output="一段市场洞察，附关键实体（品牌、公司）",
        agent=analyst,
    )
    return Crew(
        agents=[analyst],
        tasks=[task],
        process=Process.sequential,
        memory=memory,  # ← 一行开启（Short-term / Long-term / Entity）
        verbose=False,
    )


def main() -> None:
    crew = build_crew(memory=True)
    print("已开启内置 Memory 的 Crew：memory =", crew.memory)
    print("三种记忆：Short-term（本次运行）/ Long-term（跨 kickoff，SQLite）/ Entity（实体）")

    if HAS_REAL_KEY:
        print("\n检测到真实 key，连跑两次演示跨运行记忆：")
        print("第一次 kickoff：", crew.kickoff())
        print("第二次 kickoff（应自动检索上次洞察做增量）：", crew.kickoff())
    else:
        print("\n未检测到真实 OPENAI_API_KEY，跳过 kickoff()。")
        print("提示：真实运行时第二次 kickoff 会自动 search_memory 找到上次分析做增量更新。")


if __name__ == "__main__":
    main()
