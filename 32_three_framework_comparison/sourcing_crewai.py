"""采购助手 —— CrewAI 版（效率派：角色驱动 + Sequential + Memory 一行开启）。

对应文章第 32 篇「二、CrewAI 版本」。HITL 无原生支持，需自己拼（这里显式补一段）。

优先用真 crewai；缺依赖回退到系列自研 Crew（agent_examples.frameworks）：
    python3 32_three_framework_comparison/sourcing_crewai.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sourcing_common as sc  # noqa: E402

# 角色定义（role / goal / backstory）——CrewAI 的核心心智。
ROLES = [
    ("需求收集员", "把用户模糊需求整理成结构化采购单", "十年采购助理，擅长追问规格"),
    ("级联搜索员", "自家目录->供应商库->web 三级检索候选供应商", "熟悉钛合金供应链"),
    ("报价分析师", "对候选供应商重排比价并生成报告", "成本控制专家"),
    ("审批协调员", "大额订单转经理审批（HITL，CrewAI 需自拼）", "流程合规负责人"),
]


def _run_with_real_crewai(query: str) -> tuple[dict, bool]:
    """真 crewai：仅构建 Agent/Task/Crew 骨架（真实执行需 LLM key），业务用共享逻辑算确定结果。"""

    from crewai import Agent, Crew, Process, Task

    agents = [
        Agent(role=role, goal=goal, backstory=bs, verbose=False, allow_delegation=False)
        for role, goal, bs in ROLES
    ]
    tasks = [Task(description=f"{a.role}: {a.goal}", expected_output="阶段产出", agent=a) for a in agents]
    Crew(agents=agents, tasks=tasks, process=Process.sequential, memory=False)  # memory=True 一行开持久化
    return _business_pipeline(query), True


def _run_with_fallback(query: str) -> tuple[dict, bool]:
    from agent_examples.frameworks import Crew, CrewAgent

    crew = Crew(agents=[CrewAgent(role, goal) for role, goal, _ in ROLES])
    crew.kickoff(query)  # 触发角色链（自研 Crew）
    return _business_pipeline(query), False


def _business_pipeline(query: str) -> dict:
    """Sequential 里各 Task 依次产出、级联传递（业务逻辑共享，保证与其他框架结果一致）。"""

    requirements = sc.collect_requirements(query)
    searched = sc.cascade_search(requirements)
    ranked = sc.rerank_and_merge(searched["results"])
    report = sc.build_report(ranked, requirements)
    return {"requirements": requirements, "trace": searched["cascade_trace"], "ranked": ranked, "report": report}


def run(query: str = sc.DEFAULT_QUERY) -> sc.SourcingResult:
    try:
        data, used_real = _run_with_real_crewai(query)
    except ImportError:
        data, used_real = _run_with_fallback(query)

    trace = list(data["trace"])
    # HITL 自拼：CrewAI 无原生 interrupt，需要额外协调 Task（约 50-80 行）。
    if data["report"]["needs_approval"]:
        trace.append("自拼审批 Task：暂存状态 + 通知经理 + 等待回调（CrewAI 无原生 HITL）")

    return sc.SourcingResult(
        framework="CrewAI",
        intent=sc.classify_intent(query),
        requirements=data["requirements"],
        ranked=data["ranked"],
        report=data["report"],
        trace=trace,
        used_real_lib=used_real,
    )


def main() -> None:
    result = run()
    print(f"=== CrewAI 版（真实库={result.used_real_lib}）===")
    print(result.report["artifact"])
    print("\n级联/HITL 轨迹：", result.trace)


if __name__ == "__main__":
    main()
