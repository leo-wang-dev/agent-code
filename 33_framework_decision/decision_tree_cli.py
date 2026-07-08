"""选型决策树 CLI 工具 —— 从 6~7 个业务特征收敛到框架推荐。

对应文章第 33 篇「一、选型决策树」。

默认非交互（不阻塞 stdin）：不带参数时跑文章的三个示例项目 A/B/C。
也支持用参数直接给出答案，或 --interactive 逐题问：

    python3 33_framework_decision/decision_tree_cli.py                 # 跑三个内置示例
    python3 33_framework_decision/decision_tree_cli.py --high-risk no --core orchestration \\
        --complex-state no --team small
    python3 33_framework_decision/decision_tree_cli.py --interactive   # 逐题交互（可选）
"""

from __future__ import annotations

import argparse
import sys


def decide(answers: dict[str, str]) -> tuple[str, list[str]]:
    """按文章 Q1-Q7 决策树遍历，返回（推荐，走过的路径）。

    answers 可含键：high_risk / flow / gcp / core / stage / complex_state / team
    未提供的键在需要时用保守默认，路径里会标注。
    """

    path: list[str] = []

    def ask(key: str, default: str) -> str:
        val = answers.get(key)
        if val is None:
            path.append(f"{key}=?(默认 {default})")
            return default
        path.append(f"{key}={val}")
        return val

    # Q1 高风险操作（金钱/改数据/对外消息）？
    if ask("high_risk", "no") == "yes":
        # Q2 流程确定 vs 开放
        if ask("flow", "determinate") == "determinate":
            # 确定 → LangGraph 或 ADK（按生态收敛）
            return ("ADK" if ask("gcp", "no") == "yes" else "LangGraph"), path
        # 开放 → Q3 GCP 生态？
        if ask("gcp", "no") == "yes":
            return "ADK + DeepAgents 子任务", path
        return "LangGraph + DeepAgents 子任务", path

    # Q4 核心：多 Agent 协作 vs 复杂流程编排
    if ask("core", "orchestration") == "collaboration":
        # Q5 Demo/验证 vs 长期生产
        if ask("stage", "production") == "demo":
            return "CrewAI", path
        return "ADK（Sequential / Parallel Workflow）", path

    # 复杂流程编排 → Q6 需要复杂状态 / 并行 / 循环？
    if ask("complex_state", "yes") == "yes":
        return "LangGraph", path
    # Q7 团队规模 + 维护周期
    team = ask("team", "medium")
    return {"small": "CrewAI", "medium": "LangGraph", "large": "ADK"}.get(team, "LangGraph"), path


# 文章「一、决策树的执行示例」三个真实项目。
EXAMPLES = {
    "项目A HR助手(问答)": {"high_risk": "no", "core": "orchestration", "complex_state": "no", "team": "small"},
    "项目B 采购助手(审批)": {"high_risk": "yes", "flow": "determinate", "gcp": "no"},
    "项目C 金融研究(研报)": {"high_risk": "no", "core": "collaboration", "stage": "production"},
}


def _run_examples() -> None:
    print("=== 决策树内置示例（文章一节）===\n")
    for name, ans in EXAMPLES.items():
        rec, path = decide(ans)
        print(f"{name}")
        print(f"  路径：{' -> '.join(path)}")
        print(f"  推荐：{rec}\n")


def _run_interactive() -> None:
    questions = [
        ("high_risk", "Q1 涉及金钱/改数据/对外消息等高风险操作? (yes/no)"),
        ("flow", "Q2 流程确定还是开放? (determinate/open)"),
        ("gcp", "Q3 是否在 GCP/Vertex 生态? (yes/no)"),
        ("core", "Q4 核心是多Agent协作还是复杂流程编排? (collaboration/orchestration)"),
        ("stage", "Q5 Demo验证还是长期生产? (demo/production)"),
        ("complex_state", "Q6 需要复杂状态/并行/循环? (yes/no)"),
        ("team", "Q7 团队规模/周期? (small/medium/large)"),
    ]
    answers: dict[str, str] = {}
    for key, prompt in questions:
        try:
            val = input(prompt + " [回车跳过] ").strip()
        except EOFError:
            break
        if val:
            answers[key] = val
    rec, path = decide(answers)
    print(f"\n路径：{' -> '.join(path)}\n推荐：{rec}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent 框架选型决策树 CLI")
    parser.add_argument("--high-risk", choices=["yes", "no"])
    parser.add_argument("--flow", choices=["determinate", "open"])
    parser.add_argument("--gcp", choices=["yes", "no"])
    parser.add_argument("--core", choices=["collaboration", "orchestration"])
    parser.add_argument("--stage", choices=["demo", "production"])
    parser.add_argument("--complex-state", choices=["yes", "no"], dest="complex_state")
    parser.add_argument("--team", choices=["small", "medium", "large"])
    parser.add_argument("--interactive", action="store_true", help="逐题交互（默认非交互）")
    args = parser.parse_args(argv)

    if args.interactive:
        _run_interactive()
        return 0

    provided = {
        k: v
        for k, v in vars(args).items()
        if k != "interactive" and v is not None
    }
    if not provided:
        _run_examples()
        return 0

    rec, path = decide(provided)
    print("路径：", " -> ".join(path))
    print("推荐：", rec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
