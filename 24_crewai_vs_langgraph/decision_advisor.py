"""6 维度选型决策器 —— CrewAI vs LangGraph（纯 stdlib，零依赖 CLI）。

6 个维度（每个维度回答倾向，加权打分，给出推荐）：
  1. flow      流程复杂度：简单可枚举 → CrewAI；复杂分支/循环/嵌套 → LangGraph
  2. hitl      是否必须人工审批(HITL)：需要 → LangGraph
  3. persist   是否需要节点级持久化/故障恢复/审计：需要 → LangGraph
  4. sideeffect是否涉及金钱/数据操作/合规：涉及 → LangGraph
  5. team      团队与上线：小团队/缺 Agent 工程师/快速上线 → CrewAI
  6. cost      延迟/Token 成本敏感度：高度敏感 → LangGraph

用法：
  python3 decision_advisor.py                 # 跑内置示例画像（不阻塞）
  python3 decision_advisor.py --interactive   # 逐题问答
  python3 decision_advisor.py --flow complex --hitl yes --persist yes \\
          --sideeffect yes --team large --cost high   # 直接给答案

一条工程经验：不确定时选 LangGraph（复杂度上限更高，能写 80% 的 CrewAI 场景）。
"""
from __future__ import annotations

import argparse
import sys

# 每个维度：可选值 → (得分, 说明)。得分正=偏 LangGraph，负=偏 CrewAI。
DIMENSIONS = {
    "flow": {
        "question": "流程复杂度？",
        "options": {
            "simple": (-2, "步骤明确可枚举 → CrewAI"),
            "medium": (0, "中等复杂度 → 看其他维度"),
            "complex": (+2, "复杂条件分支/循环/嵌套 → LangGraph"),
        },
    },
    "hitl": {
        "question": "是否必须人工审批(HITL)？",
        "options": {
            "no": (0, "无需 HITL"),
            "yes": (+2, "必须 HITL → LangGraph 原生 interrupt"),
        },
    },
    "persist": {
        "question": "是否需要节点级持久化/故障恢复/流程审计？",
        "options": {
            "no": (0, "无强持久化需求"),
            "yes": (+2, "需要 Checkpoint/审计 → LangGraph"),
        },
    },
    "sideeffect": {
        "question": "是否涉及金钱/数据操作/合规？",
        "options": {
            "no": (0, "无高危副作用"),
            "yes": (+2, "涉及副作用/合规 → LangGraph"),
        },
    },
    "team": {
        "question": "团队与上线速度？",
        "options": {
            "small": (-2, "小团队/缺 Agent 工程师/要快 → CrewAI"),
            "large": (+1, "有工程能力，可承接模板代码 → 偏 LangGraph"),
        },
    },
    "cost": {
        "question": "延迟/Token 成本敏感度？",
        "options": {
            "low": (-1, "成本不敏感 → 偏 CrewAI 快速开发"),
            "high": (+2, "高度敏感 → LangGraph 省 30-50% token"),
        },
    },
}


def score(answers: dict) -> tuple[int, list]:
    total = 0
    detail = []
    for dim, value in answers.items():
        pts, reason = DIMENSIONS[dim]["options"][value]
        total += pts
        detail.append(f"  - {dim:<10} = {value:<8} ({pts:+d}) {reason}")
    return total, detail


def recommend(total: int) -> str:
    if total >= 3:
        return "LangGraph（工程化/持久化/复杂流程占优）"
    if total <= -3:
        return "CrewAI（角色驱动/快速上线占优）"
    return "LangGraph（临界区——不确定时选 LangGraph：复杂度上限更高，可覆盖 80% 的 CrewAI 场景）"


def evaluate(answers: dict, title: str) -> None:
    total, detail = score(answers)
    print(f"\n【{title}】")
    print("\n".join(detail))
    print(f"  综合分 = {total:+d}  →  推荐：{recommend(total)}")


def run_demo() -> None:
    print("=" * 60)
    print("6 维度选型决策器（内置示例画像）")
    print("=" * 60)
    evaluate(
        {"flow": "simple", "hitl": "no", "persist": "no",
         "sideeffect": "no", "team": "small", "cost": "low"},
        "画像A：小团队做多 Agent 内容生产（研究/写作/报告）",
    )
    evaluate(
        {"flow": "complex", "hitl": "yes", "persist": "yes",
         "sideeffect": "yes", "team": "large", "cost": "high"},
        "画像B：涉及支付+合规审计的复杂客服/工作流",
    )
    evaluate(
        {"flow": "medium", "hitl": "no", "persist": "yes",
         "sideeffect": "no", "team": "large", "cost": "high"},
        "画像C：中等复杂、注重成本与可观测",
    )
    print("\n提示：python3 decision_advisor.py --interactive 可自测你的项目。")


def run_interactive() -> None:
    answers = {}
    print("逐题回答（输入选项对应的值）：\n")
    for dim, spec in DIMENSIONS.items():
        opts = ", ".join(spec["options"].keys())
        while True:
            val = input(f"{spec['question']} [{opts}] > ").strip()
            if val in spec["options"]:
                answers[dim] = val
                break
            print("  无效选项，请重输。")
    evaluate(answers, "你的项目")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="CrewAI vs LangGraph 6 维度选型决策器")
    parser.add_argument("--interactive", action="store_true", help="逐题问答")
    for dim, spec in DIMENSIONS.items():
        parser.add_argument(f"--{dim}", choices=list(spec["options"].keys()),
                            help=spec["question"])
    args = parser.parse_args(argv)

    provided = {d: getattr(args, d) for d in DIMENSIONS if getattr(args, d)}

    if args.interactive:
        run_interactive()
    elif len(provided) == len(DIMENSIONS):
        evaluate(provided, "命令行输入的项目")
    elif provided:
        print("提示：需要提供全部 6 个维度才能直接评估；仅给出部分时改跑内置示例。\n")
        run_demo()
    else:
        run_demo()


if __name__ == "__main__":
    main()
